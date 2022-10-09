import logging
from typing import Optional
from discord import Message, Embed, TextChannel
from discord.ext import commands
from discord.ext.commands import Bot
from fastapi import FastAPI
from inhouse_bot.api_models import GameResultParams
from inhouse_bot.database_orm import session_scope


tournament_logger = logging.getLogger("tournament_handler")

class TournamentHandler:
    def __init__(self, bot: Bot, app: FastAPI):

        # Compose with a reference to the bot. Not sure if this is a good practice.
        self.bot = bot

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

        # 
        app.add_api_route("/game_result", self.game_result, methods=["POST"])
        
    async def check_tournaments(self, bot: Bot, server_id: Optional[int]):
        """
        Looks at the active tournament matches and sees if any have completed
        """
        # with session_scope() as session:
        #     channel_query = session.query(ChannelInformation).filter(ChannelInformation.id == channel_id)
        #     channel_query.delete(synchronize_session=False)
        print("check tournaments TODO")

    async def game_result(self, game_result: GameResultParams):
        # TODO

        # Update the tournament with this new result
        return game_result
