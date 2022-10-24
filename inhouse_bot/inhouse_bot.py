import logging
import os
import threading
from datetime import datetime

import discord
from discord.ext import commands


from discord.ext.commands import NoPrivateMessage
from fastapi import FastAPI

from inhouse_bot import game_queue
from inhouse_bot.common_utils.constants import (
    PREFIX,
    BACKGROUND_JOBS_INTERVAL,
    QUEUE_RESET_TIME,
)
from inhouse_bot.common_utils.docstring import doc
from inhouse_bot.common_utils.get_server_config import get_server_config
from inhouse_bot.common_utils.is_admin import AdminGroupOnly
from inhouse_bot.database_orm import session_scope
from inhouse_bot.game_queue.queue_handler import SameRolesForDuo
from inhouse_bot.queue_channel_handler.queue_channel_handler import (
    QueueChannelsOnly,
    queue_channel_handler,
)
from inhouse_bot.tournament import tournament_handler, tournament_check

# Defining intents to get full members list
from inhouse_bot.ranking_channel_handler.ranking_channel_handler import (
    ranking_channel_handler,
)

intents = discord.Intents.all()
intents.presences = False


class InhouseBot(commands.Bot):
    """
    A bot handling role-based matchmaking for LoL games
    """

    def __init__(self, app: FastAPI, **options):
        super().__init__(PREFIX, intents=intents, case_insensitive=True, **options)

        # Set up handlers if necessary
        tournament_handler.setup(bot=self, app=app)

        # Setting up the on_message listener that will handle queue channels
        self.add_listener(
            queue_channel_handler.queue_channel_message_listener, "on_message"
        )

        # Setting up some basic logging
        self.logger = logging.getLogger("inhouse_bot")

        self.add_listener(self.command_logging, "on_command")

    async def setup_hook(self) -> None:
        # Importing locally to allow InhouseBot to be imported in the cogs
        from inhouse_bot.cogs.queue_cog import QueueCog
        from inhouse_bot.cogs.admin_cog import AdminCog
        from inhouse_bot.cogs.stats_cog import StatsCog

        # Putting this here because there's not a category that makes sense yet
        @commands.command()
        @doc(f"Displays the running bot version")
        async def version(ctx: commands.Context):
            version = os.getenv("VERSION")
            await ctx.send(version)

        self.add_command(version)

        await self.add_cog(QueueCog(self))
        await self.add_cog(AdminCog(self))
        await self.add_cog(StatsCog(self))

        # While I hate mixing production and testing code, this is the most convenient solution to test the bot
        if os.environ.get("INHOUSE_BOT_TEST"):
            from tests.test_cog import TestCog

            await self.add_cog(TestCog(self))

    async def start(self, *args, **kwargs):
        await super().start(os.environ["INHOUSE_BOT_TOKEN"], *args, **kwargs)

    async def command_logging(self, ctx: discord.ext.commands.Context):
        """
        Listener called on command-trigger messages to add some logging
        """
        self.logger.info(
            f"{ctx.message.content}\t{ctx.author.name}\t{ctx.guild.name}\t{ctx.channel.name}"
        )

    def background_jobs(self):
        """
        Triggers background jobs and sets a timer to execute them again on a timeout.
        No work should be done in this thread -- jobs should only get added to the event loop
        """
        now = datetime.now()

        try:
            with session_scope() as session:
                # TODO this only retrieves the config for the first guild.
                # This could cause problems if the bot is in multiple guilds.
                config = get_server_config(
                    server_id=self.guilds[0].id, session=session
                ).config

            if now.strftime("%H:%M") == QUEUE_RESET_TIME:
                if config["queue_reset"]:
                    game_queue.reset_queue()
                    self.loop.create_task(
                        queue_channel_handler.update_queue_channels(
                            bot=self, server_id=None
                        )
                    )

            if config["tournament"]:
                self.loop.create_task(tournament_check(bot=self, server_id=None))
        except Exception as e:
            self.logger.error(f"[Background Job Scheduler] error {e}")
        finally:
            # Always make sure the next jobs are scheduled
            threading.Timer(BACKGROUND_JOBS_INTERVAL, self.background_jobs).start()

    async def on_ready(self):
        self.logger.info(f"{self.user.name} has connected to Discord")

        # We cancel all ready-checks, and queue_channel_handler will handle rewriting the queues
        game_queue.cancel_all_ready_checks()

        await queue_channel_handler.update_queue_channels(bot=self, server_id=None)
        await ranking_channel_handler.update_ranking_channels(bot=self, server_id=None)

        # Starts the scheduler
        self.background_jobs()

    async def on_command_error(self, ctx, error):
        """
        Custom error command that catches CommandNotFound as well as MissingRequiredArgument for readable feedback
        """
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(
                f"Command `{ctx.invoked_with}` not found, use {PREFIX}help to see the commands list"
            )

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"Arguments missing, use `{PREFIX}help {ctx.invoked_with}` to see the arguments list"
            )

        elif isinstance(error, commands.ConversionError):
            # Conversion errors feedback are handled in my converters
            pass

        elif isinstance(error, NoPrivateMessage):
            await ctx.send(f"This command can only be used inside a server")

        elif isinstance(error, QueueChannelsOnly):
            await ctx.send(
                f"This command can only be used in a channel marked as a queue by an admin"
            )

        elif isinstance(error, SameRolesForDuo):
            await ctx.send(f"Duos must have different roles")

        elif isinstance(error, AdminGroupOnly):
            await ctx.send(f"Only admins can use this command")

        # This handles errors that happen during a command
        elif isinstance(error, commands.CommandInvokeError):
            og_error = error.original

            if isinstance(og_error, game_queue.PlayerInGame):
                await ctx.send(
                    f"Your last game was not scored and you are not allowed to queue at the moment\n"
                    f"One of the winners can score the game with `{PREFIX}won`, "
                    f"or players can agree to cancel it with `{PREFIX}cancel`",
                    delete_after=20,
                )

            elif isinstance(og_error, game_queue.PlayerInReadyCheck):
                await ctx.send(
                    f"A game has already been found for you and you cannot queue until it is accepted or cancelled\n"
                    f"If it is a bug, post in #bot-dev-and-spam and ask them to use `{PREFIX}admin reset` with your name",
                    delete_after=20,
                )

            else:
                # User-facing error
                await ctx.send(
                    f"There was an error processing the command\n"
                    f"Use {PREFIX}help for the commands list or post in #bot-dev-and-spam for bugs",
                )

                self.logger.error(og_error)

        else:
            # User-facing error
            await ctx.send(
                f"There was an error processing the command\n"
                f"Use {PREFIX}help for the commands list or post in #bot-dev-and-spam for bugs",
            )

            self.logger.error(error)
