import asyncio
import logging
from typing import List, Set, Union
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
from inhouse_bot.database_orm.session.session import Session
from inhouse_bot.common_utils.lol_api.tasks import (
    get_match_info_by_id,
    get_provider,
    get_summoner_by_name,
    get_summoner_by_puuid,
    get_tournament,
    get_tournament_codes,
)
from inhouse_bot.database_orm.tables.game import Game
from inhouse_bot.database_orm.tables.tournament import Tournament
from urllib.parse import urljoin
import secrets


class TournamentHandler:
    bot: Union[Bot, None] = None
    app: Union[FastAPI, None] = None

    provider: int = 0

    def __init__(self):
        # Grab active tournaments on initialize TODO
        with session_scope() as session:
            session.expire_on_commit = False

            # self._queue_channels = (
            #     session.query(ChannelInformation.id, ChannelInformation.server_id)
            #     .filter(ChannelInformation.channel_type == "QUEUE")
            #     .all()
            # )

    async def _setup_provider(self):
        if not INHOUSE_BOT_TOURNAMENT_URL:
            raise Exception("INHOUSE_BOT_TOURNAMENT_URL not set")

        # e.g. https://hostname/game_result
        callback_url = urljoin(INHOUSE_BOT_TOURNAMENT_URL, "game_result")

        self.provider = await get_provider(callback_url)
        logging.info(
            "Created tournament provider: id=%s url=%s",
            self.provider,
            INHOUSE_BOT_TOURNAMENT_URL,
        )
        return 0

    async def setup(self, bot: Bot, app: FastAPI):
        """
        Setup the tournament handler. This only needs to be called once when the bot is initialized.
        """
        self.bot = bot
        await self._setup_provider()

        # Handle the game_result route
        app.add_api_route("/game_result", self._game_result, methods=["POST"])

        # check for the INHOUSE_BOT_TEST environment variable
        if INHOUSE_BOT_TEST:
            # capture other routes
            app.add_api_route(
                "/{path_name:path}", self._fallback, methods=["GET", "POST"]
            )

        logging.info("Initialized tournament handler")

    async def create_tournament(self, game: Game) -> Tournament:
        """
        Create a Tournament entity for the given Game. It does not add it to the database.
        """
        summoners = await asyncio.gather(
            *[
                get_summoner_by_puuid(puuid)
                for puuid in game.player_puuids
                if bool(puuid)
            ]
        )

        summoners.append(await get_summoner_by_name("Azula"))

        # map_type = "SUMMONERS_RIFT"
        map_type = "HOWLING_ABYSS"
        pick_type = "TOURNAMENT_DRAFT"
        team_size = 1
        spectator_type = "LOBBYONLY"
        allowed_summoner_ids = [summoner.id for summoner in summoners]

        # tournament_id = await get_tournament(
        #     name=game.id, provider_id=self.provider
        # )
        tournament_id = 2646831

        # generate a secure random string
        tournament_secret = secrets.token_urlsafe(16)

        codes = ["NA04b7e-f0afbbe6-3852-47c9-a5df-472fc33d92fd"]
        # codes = await get_tournament_codes(
        #     tournament_id=tournament_id,
        #     map_type=map_type,
        #     pick_type=pick_type,
        #     team_size=team_size,
        #     count=1,
        #     spectator_type=spectator_type,
        #     allowed_summoner_ids=allowed_summoner_ids,
        #     metadata=tournament_secret,
        # )

        code = codes[0]

        # create the Tournament entity
        tournament = Tournament(
            code=code,
            game=game,
            name=game.id,
            tournament_id=tournament_id,
            provider_id=self.provider,
            allowed_summoner_ids=allowed_summoner_ids,
            team_size=team_size,
            pick_type=pick_type,
            spectator_type=spectator_type,
            map_type=map_type,
            game_id=game.id,
            tournament_metadata=tournament_secret,
        )

        return tournament

    async def _fallback(self, request: Request, path_name: str):
        body = await request.body()
        print(request.query_params, body, path_name)
        return {"request_method": request.method, "path_name": path_name}

    # API route handler function
    async def _game_result(self, game_result: GameResultParams):
        # TODO Update the tournament with this new result

        with session_scope() as session:
            code = game_result.shortCode
            tournament: Tournament | None = (
                session.query(Tournament).filter(Tournament.code == code).first()
            )

            if tournament is None:
                logging.error("Tournament not found: tournament_id=%s", code)
                return

            # verify the tournament secret
            if tournament.tournament_metadata != game_result.metaData:
                logging.error(
                    "Tournament secret does not match: tournament_id=%s, game_result.metaData=%s",
                    code,
                    game_result.metaData,
                )
                return

            # i.e. NA1_1234567890
            tournament.match_id = f"{game_result.region}_{game_result.gameId}"

            # get the match details from the riot API
            match = await get_match_info_by_id(tournament.match_id)

            # first team is always blue team I think? (teamid 100)
            # if match.info.teams[0].win:
            # await
            # merge the tournament into the database
            session.merge(tournament)

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
