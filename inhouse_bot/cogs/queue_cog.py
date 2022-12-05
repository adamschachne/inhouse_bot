import logging
import discord
import random

from datetime import datetime, timedelta
from discord.ext import commands

from inhouse_bot import game_queue
from inhouse_bot import matchmaking_logic

from inhouse_bot.common_utils.constants import INHOUSE_BOT_TOURNAMENTS, PREFIX
from inhouse_bot.common_utils.docstring import doc
from inhouse_bot.common_utils.emoji_and_thumbnails import get_role_emoji
from inhouse_bot.common_utils.fields import QueueRoleConverter, roles_list
from inhouse_bot.common_utils.get_last_game import get_last_game
from inhouse_bot.common_utils.get_player import get_player
from inhouse_bot.common_utils.lol_api.tasks import (
    get_profile_icon_by_id,
    get_summoner_by_name,
)
from inhouse_bot.common_utils.set_player_summoner_puuid import set_player_summoner
from inhouse_bot.common_utils.validation_dialog import checkmark_validation
from inhouse_bot.common_utils.is_verified_user import are_verified_users

from inhouse_bot.database_orm import session_scope
from inhouse_bot.database_orm.tables.game import Game
from inhouse_bot.database_orm.tables.tournament import Tournament
from inhouse_bot.inhouse_bot import InhouseBot
from inhouse_bot.queue_channel_handler.queue_channel_handler import (
    queue_channel_handler,
    queue_channel_only,
)
from inhouse_bot.ranking_channel_handler.ranking_channel_handler import (
    ranking_channel_handler,
)
from inhouse_bot.tournament import tournament_handler
from inhouse_bot.voice_channel_handler.voice_channel_handler import (
    create_voice_channels,
    remove_voice_channels,
)


class QueueCog(commands.Cog, name="Queue"):
    """
    Manage your queue status and score games
    """

    def __init__(self, bot: InhouseBot):
        self.bot = bot

        # Makes them jump ahead on the next queue
        #   player_id -> timestamp
        self.players_whose_last_game_got_cancelled = {}

        self.games_getting_scored_ids = set()

        # uncomment this code to disable !won
        # It's left because players may use the Tournament feature incorrectly and need to score their games manually
        # if INHOUSE_BOT_TOURNAMENTS:
        #     self.bot.remove_command(self.won.name)

    async def run_matchmaking_logic(
        self,
        ctx: commands.Context,
    ):
        """
        Runs the matchmaking logic in the channel defined by the context

        Should only be called inside guilds
        """
        queue = game_queue.GameQueue(ctx.channel.id)

        game = await matchmaking_logic.find_best_game(queue)

        if not game:
            return

        elif game:
            embed = game.get_embed(
                embed_type="GAME_FOUND", validated_players=[], bot=self.bot
            )

            # We notify the players and send the message
            ready_check_message = await ctx.send(
                content=game.players_ping, embed=embed, delete_after=60 * 15
            )

            # We mark the ready check as ongoing (which will be used to the queue)
            game_queue.start_ready_check(
                player_ids=game.player_ids_list,
                channel_id=ctx.channel.id,
                ready_check_message_id=ready_check_message.id,
            )

            # We update the queue in all channels
            await queue_channel_handler.update_queue_channels(
                bot=self.bot, server_id=ctx.guild.id
            )

            # And then we wait for the validation
            try:
                ready, players_to_drop = await checkmark_validation(
                    bot=self.bot,
                    message=ready_check_message,
                    validating_players_ids=game.player_ids_list,
                    validation_threshold=10,
                    game=game,
                )

            # We catch every error here to make sure it does not become blocking
            except Exception as e:
                logging.error(e)
                game_queue.cancel_ready_check(
                    ready_check_id=ready_check_message.id,
                    ids_to_drop=game.player_ids_list,
                    server_id=ctx.guild.id,
                )
                await ctx.send(
                    "There was a bug with the ready-check message, all players have been dropped from queue\n"
                    "Please queue again to restart the process"
                )

                await queue_channel_handler.update_queue_channels(
                    bot=self.bot, server_id=ctx.guild.id
                )

                return

            if ready is True:
                # We drop all 10 players from the queue
                game_queue.remove_players_from_queue(ready_check_message.id)

                tournament: Tournament | None = None

                # We commit the game to the database (without a winner)
                with session_scope() as session:
                    session.expire_on_commit = False

                    # create a transaction savepoint to rollback to if there is an error
                    with session.begin_nested():
                        game = session.merge(game)  # This gets us the game ID

                        # need to commit in order to get the game id
                        session.commit()

                        if INHOUSE_BOT_TOURNAMENTS:
                            # Create a tournament code if the feature is enabled
                            tournament = await tournament_handler.create_tournament(
                                game=game
                            )

                            # add the tournament code to the database
                            session.add(tournament)

                # accounce in the channel that the game is created
                queue_channel_handler.mark_queue_related_message(
                    await ctx.send(
                        embed=game.get_embed(
                            embed_type="GAME_ACCEPTED",
                            tournament_code=tournament.code if tournament else None,
                        )
                    )
                )

                # We create voice channels for each team in this game
                await create_voice_channels(ctx, game)

            elif ready is False:
                # We remove the player who cancelled
                game_queue.cancel_ready_check(
                    ready_check_id=ready_check_message.id,
                    ids_to_drop=players_to_drop,
                    channel_id=ctx.channel.id,
                )

                await ctx.send(
                    f"A player cancelled the game and was removed from the queue\n"
                    f"All other players have been put back in the queue",
                )

                # We restart the matchmaking logic
                await self.run_matchmaking_logic(ctx)

            elif ready is None:
                # We remove the timed out players from *all* channels (hence giving server id)
                game_queue.cancel_ready_check(
                    ready_check_id=ready_check_message.id,
                    ids_to_drop=players_to_drop,
                    server_id=ctx.guild.id,
                )

                await ctx.send(
                    "The check timed out and players who did not answer have been dropped from all queues",
                )

                # We restart the matchmaking logic
                await self.run_matchmaking_logic(ctx)

    @commands.command(aliases=["view_queue", "refresh"])
    @queue_channel_only()
    async def view(
        self,
        ctx: commands.Context,
    ):
        """
        Refreshes the queue in the current channel

        Almost never needs to get used directly
        """
        await queue_channel_handler.update_queue_channels(
            bot=self.bot, server_id=ctx.guild.id
        )

    @commands.command()
    @queue_channel_only()
    @doc(
        f"""
        Adds you to the current channel’s queue for the given role

        To duo queue, add @player role at the end (cf examples)

        Roles are TOP, JGL, MID, BOT/ADC, and SUP

        Example:
            {PREFIX}queue SUP
            {PREFIX}queue bot
            {PREFIX}queue adc
            {PREFIX}queue all
            {PREFIX}queue adc @CoreJJ support
    """
    )
    async def queue(
        self,
        ctx: commands.Context,
        role: QueueRoleConverter,
        duo: discord.Member = None,
        duo_role: QueueRoleConverter = None,
    ):
        server_id = ctx.guild.id

        # Check if user is verified before allowing them to use queue
        usersToVerify = [ctx.author.id]
        if duo:
            usersToVerify.append(duo.id)

        if not await are_verified_users(ctx, usersToVerify, server_id):
            return

        # Checking if the last game of this player got cancelled
        #   If so, we put them in the queue in front of other players
        jump_ahead = False

        # pop with two arguments returns the second one if the key was not found
        if cancel_timestamp := self.players_whose_last_game_got_cancelled.pop(
            ctx.author.id, None
        ):

            if datetime.now() - cancel_timestamp < timedelta(hours=1):
                jump_ahead = True

        if not duo:
            if role == "ALL":
                for r in roles_list:
                    # Simply queuing the player
                    await game_queue.add_player(
                        player_id=ctx.author.id,
                        name=ctx.author.display_name,
                        role=r,
                        channel_id=ctx.channel.id,
                        server_id=server_id,
                        jump_ahead=jump_ahead,
                    )
            else:
                # Simply queuing the player
                await game_queue.add_player(
                    player_id=ctx.author.id,
                    name=ctx.author.display_name,
                    role=role,
                    channel_id=ctx.channel.id,
                    server_id=server_id,
                    jump_ahead=jump_ahead,
                )

        # If there is a duo, we go for a different flow (which should likely be another function)
        else:
            if not duo_role:
                await ctx.send("You need to input a role for your duo partner")
                return

            if role == "ALL" or duo_role == "ALL":
                await ctx.send("Duos cannot queue for all roles")
                return

            duo_validation_message = await ctx.send(
                f"<@{ctx.author.id}> {get_role_emoji(role)} wants to duo with <@{duo.id}> {get_role_emoji(duo_role)}\n"
                f"Press ✅ to accept the duo queue"
            )

            validated, players_who_refused = await checkmark_validation(
                bot=self.bot,
                message=duo_validation_message,
                validating_players_ids=[duo.id],
                validation_threshold=1,
            )

            if not validated:
                await ctx.send(f"<@{ctx.author.id}>: Duo queue was refused")
                return

            # Here, we have a working duo queue
            await game_queue.add_duo(
                first_player_id=ctx.author.id,
                first_player_role=role,
                first_player_name=ctx.author.display_name,
                second_player_id=duo.id,
                second_player_role=duo_role,
                second_player_name=duo.display_name,
                channel_id=ctx.channel.id,
                server_id=server_id,
                jump_ahead=jump_ahead,
            )

        await self.run_matchmaking_logic(ctx=ctx)

        await queue_channel_handler.update_queue_channels(
            bot=self.bot, server_id=server_id
        )

    @commands.command(aliases=["leave_queue", "stop"])
    @queue_channel_only()
    @doc(
        f"""
        Removes you from the queue in the current channel

        Example:
            {PREFIX}leave
            {PREFIX}leave bot
            {PREFIX}leave jg
            {PREFIX}leave_queue

    """
    )
    async def leave(
        self,
        ctx: commands.Context,
        role: QueueRoleConverter() = None,
    ):
        game_queue.remove_player(
            player_id=ctx.author.id, channel_id=ctx.channel.id, role=role
        )
        await queue_channel_handler.update_queue_channels(
            bot=self.bot, server_id=ctx.guild.id
        )

    @commands.command(aliases=["win", "wins", "victory"])
    @queue_channel_only()
    @doc(
        f"""
        Scores your last game as a win

        Will require validation from at least 6 players in the game

        Example:
            {PREFIX}won
    """
    )
    async def won(
        self,
        ctx: commands.Context,
    ):
        with session_scope() as session:
            session.expire_on_commit = False
            # Get the latest game
            game, participant = get_last_game(
                player_id=ctx.author.id, server_id=ctx.guild.id, session=session
            )

            if not game or not participant:
                await ctx.send("You have not played a game on this server yet")
                return

            elif game and game.winner:
                await ctx.send(
                    "Your last game seem to have already been scored\n"
                    "If there was an issue, please contact an admin"
                )
                return

            elif game.id in self.games_getting_scored_ids:
                await ctx.send(
                    "There is already a scoring or cancellation message active for this game"
                )
                return

            else:
                self.games_getting_scored_ids.add(game.id)

            win_validation_message = await ctx.send(
                f"{game.players_ping}"
                f"{ctx.author.display_name} wants to score game {game.id} as a win for {participant.side.value}\n"
                f"Result will be validated once 6 players from the game press ✅"
            )

            validated, players_who_refused = await checkmark_validation(
                bot=self.bot,
                message=win_validation_message,
                validating_players_ids=game.player_ids_list,
                validation_threshold=6,
            )

            # Whatever happens, we’re not scoring it anymore if we get here
            self.games_getting_scored_ids.remove(game.id)

            if not validated:
                await ctx.send("Score input was either cancelled or timed out")
                return

        # If we get there, the score was validated and we can simply update the game and the ratings
        queue_channel_handler.mark_queue_related_message(
            await ctx.send(
                f"Game {game.id} has been scored as a win for {participant.side.value} and ratings have been updated"
            )
        )

        matchmaking_logic.score_game_from_winning_player(
            player_id=ctx.author.id, server_id=ctx.guild.id
        )
        await ranking_channel_handler.update_ranking_channels(self.bot, ctx.guild.id)

        # If we're here, the game has been scored and the voice channels for this game can be removed
        await remove_voice_channels(ctx, game)

    @commands.command(aliases=["cancel_game"])
    @queue_channel_only()
    @doc(
        f"""
        Cancels your ongoing game

        Will require validation from at least 6 players in the game

        Example:
            {PREFIX}cancel
    """
    )
    async def cancel(
        self,
        ctx: commands.Context,
    ):
        with session_scope() as session:
            # Get the latest game
            game, participant = get_last_game(
                player_id=ctx.author.id, server_id=ctx.guild.id, session=session
            )

            # either there is no game or the last game has a winner (game has finished)
            if game is None or game.winner:
                await ctx.send("It does not look like you are part of an ongoing game")
                return

            elif game.id in self.games_getting_scored_ids:
                await ctx.send(
                    "There is already a scoring or cancellation message active for this game"
                )
                return

            else:
                self.games_getting_scored_ids.add(game.id)

            cancel_validation_message = await ctx.send(
                f"{game.players_ping}"
                f"{ctx.author.display_name} wants to cancel game {game.id}\n"
                f"Game will be canceled once 6 players from the game press ✅"
            )

            validated, players_who_refused = await checkmark_validation(
                bot=self.bot,
                message=cancel_validation_message,
                validating_players_ids=game.player_ids_list,
                validation_threshold=6,
            )

            self.games_getting_scored_ids.remove(game.id)

            if not validated:
                await ctx.send(f"Game {game.id} was not cancelled")

            else:

                for participant in game.participants.values():
                    self.players_whose_last_game_got_cancelled[
                        participant.player_id
                    ] = datetime.now()

                await remove_voice_channels(ctx, game)
                session.delete(game)

                queue_channel_handler.mark_queue_related_message(
                    await ctx.send(f"Game {game.id} was cancelled")
                )

    @commands.command()
    @queue_channel_only()
    @doc(
        f"""
        Verifies your Summoner name

        Example:
            {PREFIX}verify Doublelift
    """
    )
    async def verify(
        self,
        ctx: commands.Context,
        *name_arg: str,
    ):
        if not name_arg:
            await ctx.send("Please provide a summoner name")
            return

        summoner_name = " ".join(name_arg)

        summoner = await get_summoner_by_name(summoner_name, no_cache=True)

        # get the player from the database
        player = get_player(player_id=ctx.author.id, server_id=ctx.guild.id)
        if player and player.summoner_puuid == summoner.puuid:
            await ctx.send("Your summoner name is already verified")
            return

        # Use icons 1 through 28 for verification -- excluding the current profile icon
        verification_icons_ids = [
            i for i in range(1, 29) if i is not summoner.profile_icon.id
        ]
        icon = await get_profile_icon_by_id(
            icon_id=random.choice(verification_icons_ids)
        )

        verification_message = await ctx.send(
            f"You are verifying the summoner name: `{summoner.name}`\n"
            + "Please change your Summoner icon to the following icon\n"
            + "Press ✅ once you have done so, or ❌ to cancel\n",
            file=discord.File(f"assets/profile-icons/{icon.id}.jpg"),
        )

        result, ids_to_drop = await checkmark_validation(
            bot=self.bot,
            message=verification_message,
            validation_threshold=1,
            timeout=120,
            validating_players_ids=[ctx.author.id],
        )

        if ids_to_drop or result is False:
            await ctx.send("Verification was cancelled or timed out")
            return

        # If we get here, the the author pressed the checkmark --> we can now verify the summoner icon
        summoner = await get_summoner_by_name(summoner_name, no_cache=True)
        if summoner.profile_icon.id is not icon.id:
            await ctx.send(
                f"Verification failed: Your profile icon is not the one shown in the message"
            )
            return

        set_player_summoner(
            server_id=ctx.guild.id,
            user_id=ctx.author.id,
            summoner_puuid=summoner.puuid,
            summoner_name=summoner.name,
        )

        await ctx.send(f"Verified Summoner name: {summoner.name}")
