import asyncio
import logging
import secrets
from typing import Callable, List, Set, Union
from discord import Message, Embed, TextChannel
from discord.ext import commands
from discord.ext.commands import Bot
from fastapi import FastAPI, Request
from urllib.parse import urljoin

from inhouse_bot import matchmaking_logic
from inhouse_bot.api_models import GameResultParams
from inhouse_bot.common_utils.constants import (
    INHOUSE_BOT_TEST,
    INHOUSE_BOT_TOURNAMENT_URL,
    INHOUSE_BOT_TOURNAMENTS,
)
from inhouse_bot.common_utils.fields import SideEnum
from inhouse_bot.common_utils.get_server_admins import get_server_admins
from inhouse_bot.database_orm import session_scope
from inhouse_bot.database_orm.session.session import Session
from inhouse_bot.common_utils.lol_api.tasks import (
    get_match_info_by_id,
    get_provider,
    get_summoner_by_puuid,
    get_tournament,
    get_tournament_codes,
)
from inhouse_bot.database_orm.tables.game import Game
from inhouse_bot.database_orm.tables.game_participant import GameParticipant
from inhouse_bot.database_orm.tables.tournament import Tournament
from inhouse_bot.queue_channel_handler.queue_channel_handler import (
    queue_channel_handler,
)
from inhouse_bot.ranking_channel_handler.ranking_channel_handler import (
    ranking_channel_handler,
)

from pyot.models.lol.match import Match


class TournamentHandler:
    bot: Bot
    provider: int = 0

    def __init__(self):
        pass

    async def _setup_provider(self):
        if not INHOUSE_BOT_TOURNAMENT_URL:
            raise Exception("INHOUSE_BOT_TOURNAMENT_URL not set")

        # e.g. https://hostname/game_result
        callback_url = urljoin(INHOUSE_BOT_TOURNAMENT_URL, "game_result")

        self.provider = await get_provider(callback_url)
        logging.info(
            "Created tournament provider: id=%s url=%s",
            self.provider,
            callback_url,
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

        puuids: Set[str] = set()

        # add all players in the game
        for puuid in game.player_puuids:
            puuids.add(puuid)

        # add admins for the server
        for admin in get_server_admins(server_id=game.server_id):
            if admin.summoner_puuid is not None:
                puuids.add(admin.summoner_puuid)

        # get the summoners of the players in the game and the admins on the server
        summoners = await asyncio.gather(
            *[get_summoner_by_puuid(puuid) for puuid in list(puuids)]
        )

        map_type = "SUMMONERS_RIFT"
        pick_type = "TOURNAMENT_DRAFT"
        team_size = 5
        spectator_type = "LOBBYONLY"
        allowed_summoner_ids = [summoner.id for summoner in summoners]

        tournament_id = await get_tournament(
            name=str(game.id), provider_id=self.provider
        )

        # generate a secure random string
        tournament_secret = secrets.token_urlsafe(16)

        codes = await get_tournament_codes(
            tournament_id=tournament_id,
            map_type=map_type,
            pick_type=pick_type,
            team_size=team_size,
            count=1,
            spectator_type=spectator_type,
            allowed_summoner_ids=allowed_summoner_ids,
            metadata=tournament_secret,
        )

        code = codes[0]

        # create the Tournament entity
        tournament = Tournament(
            code=code,
            game=game,
            name=str(game.id),
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

    async def score_tournament(
        self, tournament: Tournament, match: Match, session: Session
    ) -> SideEnum | None:
        """
        Scores the given tournament based on the given match. The tournament match_id is set,
        Game participants' champions are updated, the game winner is set.
        """
        # i.e. NA1_1234567890
        tournament.match_id = match.metadata.match_id
        # a mapping of player puuid to match player
        players_by_puuid = {player.puuid: player for player in match.info.participants}

        # A GameParticipant from the winning team. It doesn't matter which one.
        any_winning_player: GameParticipant | None = None

        # iterate the game participants and set their champion id
        for participant in tournament.game.participants.values(): # type: ignore
            if not isinstance(participant, GameParticipant):
                continue

            puuid = participant.player.summoner_puuid
            if not isinstance(puuid, str):
                continue

            player = players_by_puuid.get(puuid, None)

            # if this player is not in the GameParticipants, there's nothing to do. This could
            # only happen if the player was an admin and not a player in the game, or if Riot
            # the puuids of the players in the game were different from the puuids of GameParticipants
            if not player:
                continue

            if player.win == True:
                any_winning_player = participant

            participant.champion_id = player.champion_id

        # this should always be true if the game has a winner, but just in case
        if any_winning_player is not None:
            matchmaking_logic.score_game_from_winning_player(
                player_id=any_winning_player.player_id,
                server_id=tournament.game.server_id,
                session=session,
            )

            session.merge(tournament)

            return any_winning_player.side
        return None

    async def send_server_game_result(
        self, game_id: int, server_id: int, winning_side: SideEnum
    ):
        """
        Send the game result to the server.
        """
        await ranking_channel_handler.update_ranking_channels(
            bot=self.bot, server_id=server_id
        )
        # get the queue channel for this game's server from queue_channel_handler
        queue_channel_id = queue_channel_handler.get_server_queues(server_id)[0]

        channel = self.bot.get_channel(queue_channel_id)

        if isinstance(channel, TextChannel):
            queue_channel_handler.mark_queue_related_message(
                await channel.send(
                    f"Game {game_id} has been scored as a win for {winning_side}!"
                )
            )

    async def _fallback(self, request: Request, path_name: str):
        body = await request.body()
        print(request.query_params, body, path_name)
        return {"request_method": request.method, "path_name": path_name}

    # API route handler function
    async def _game_result(self, game_result: GameResultParams):
        server_id: int = -1
        game_id: int = -1
        winning_side: SideEnum | None = None

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

            if tournament.game.winner is not None:
                logging.error(
                    "Game already has a winner: tournament_id=%s, game_id=%s",
                    code,
                    tournament.game.id,
                )
                return

            game_id = tournament.game_id
            server_id = tournament.game.server_id
            # get the match details from the riot API
            match = await get_match_info_by_id(
                f"{game_result.region}_{game_result.gameId}"
            )

            winning_side = await self.score_tournament(
                tournament=tournament, match=match, session=session
            )

        # after the session is closed and committed, the game result can be sent to the game server's channels
        try:
            if winning_side is not None:
                await self.send_server_game_result(
                    game_id=game_id, server_id=server_id, winning_side=winning_side
                )
        except:
            # do nothing if there is no queue channel
            pass

        return {"message": "Success"}


# Singleton export
tournament_handler = TournamentHandler()
