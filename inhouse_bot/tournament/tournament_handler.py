import logging
from typing import Union
from discord import Message, Embed, TextChannel
from discord.ext import commands
from discord.ext.commands import Bot
from fastapi import FastAPI, Request
from inhouse_bot.api_models import GameResultParams
from inhouse_bot.common_utils.constants import (
    INHOUSE_BOT_TEST,
    INHOUSE_BOT_TOURNAMENT_URL,
    INHOUSE_BOT_TOURNAMENTS,
)
from inhouse_bot.database_orm import session_scope
from inhouse_bot.common_utils.lol_api.tasks import create_provider


class TournamentHandler:
    bot: Union[Bot, None] = None
    app: Union[FastAPI, None] = None

    provider: int = 0

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

    async def setup_provider(self):
        if not INHOUSE_BOT_TOURNAMENT_URL:
            raise Exception("INHOUSE_BOT_TOURNAMENT_URL not set")

        self.provider = await create_provider(INHOUSE_BOT_TOURNAMENT_URL)
        logging.info(
            "Created tournament provider: id=%s url=%s",
            self.provider,
            INHOUSE_BOT_TOURNAMENT_URL,
        )
        return 0

    async def setup(self, bot: Bot, app: FastAPI):
        self.bot = bot
        await self.setup_provider()

        # Handle the game_result route
        app.add_api_route("/game_result", self.game_result, methods=["POST"])

        # check for the INHOUSE_BOT_TEST environment variable
        if INHOUSE_BOT_TEST:
            # capture other routes
            app.add_api_route(
                "/{path_name:path}", self.fallback, methods=["GET", "POST"]
            )

        logging.info("Initialized tournament handler")

    async def fallback(self, request: Request, path_name: str):
        body = await request.body()
        print(request.query_params, body, path_name)
        return {"request_method": request.method, "path_name": path_name}

    # API route handler function
    async def game_result(self, game_result: GameResultParams):
        # TODO Update the tournament with this new result
        if self.tournaments_cache.get(game_result.gameId, None) is None:
            logging.error(
                "Tournament not found in cache: tournament_id=%s", game_result.gameId
            )
            return {"message": "Tournament not found in cache"}
        return {"message": "Success"}


# Singleton export
tournament_handler = TournamentHandler()


def tournament_api_check(is_enabled: bool):
    """
    This is a command decorator that enables the command if TOURNAMENT_API env variable is the same as is_enabled
    """

    def decorator(func):
        if bool(INHOUSE_BOT_TOURNAMENTS) != is_enabled:
            return
        return func

    return decorator
