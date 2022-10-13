import logging
from typing import Union
from discord import Message, Embed, TextChannel
from discord.ext import commands
from discord.ext.commands import Bot
from fastapi import FastAPI
from inhouse_bot.api_models import GameResultParams
from inhouse_bot.database_orm import session_scope


tournament_logger = logging.getLogger("tournament_handler")


class TournamentHandler:
    bot: Union[Bot, None] = None
    app: Union[FastAPI, None] = None

    def __init__(self):
        # Tournaments
        self.tournaments_cache = {}

        # Grab active tournaments on initialize TODO
        with session_scope() as session:
            session.expire_on_commit = False

            # self._queue_channels = (
            #     session.query(ChannelInformation.id, ChannelInformation.server_id)
            #     .filter(ChannelInformation.channel_type == "QUEUE")
            #     .all()
            # )

    def setup(self, bot: Bot, app: FastAPI):
        self.bot = bot
        self.app = app

        # Handle the game_result route
        app.add_api_route("/game_result", self.game_result, methods=["POST"])

    # API route handler function
    async def game_result(self, game_result: GameResultParams):
        # TODO Update the tournament with this new result
        return game_result


# Singleton export
tournament_handler = TournamentHandler()
