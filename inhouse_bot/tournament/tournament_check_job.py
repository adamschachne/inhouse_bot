import logging
import random
from discord.ext import commands
from typing import List, Optional, Tuple
from inhouse_bot.common_utils.lol_api.tasks import (
    get_match_info_by_id,
    get_tournament_match_history,
)

from inhouse_bot.database_orm import session_scope
from inhouse_bot.database_orm.session.session import Session
from inhouse_bot.database_orm.tables.game import Game
from inhouse_bot.database_orm.tables.tournament import Tournament

from inhouse_bot.tournament.tournament_handler import tournament_handler


def get_active_games(session: Session) -> List[Tuple[Game, Tournament]]:
    return (
        session.query(Game, Tournament)
        .select_from(Game)
        .outerjoin(Tournament)
        .filter(Game.winner == None)
        .all()
    )


async def tournament_check(bot: commands.Bot, server_id: int):
    """
    Tournaments background job. This looks at the active games and tries to find a completed tournament match
    """

    logging.info("Checking for completed matches")
    with session_scope() as session:
        # query for tournaments whose games do not have a winner
        for game, tournament in get_active_games(session):
            logging.info(f"Game {game.id} is still active. Checking for updates.")

            start_timestamp = int(game.start.timestamp())

            # Find a player in the game and search their tournament match history after the game start time
            # The player is chosen at random because it doesn't matter which player we use, but some players
            # may have played more tournament matches than others.
            player_puuid = random.choice(
                list(filter(lambda puuid: puuid, game.player_puuids))
            )
            match_history = await get_tournament_match_history(
                puuid=player_puuid, start_timestamp=start_timestamp
            )

            for match_id in match_history.ids:
                # get the match info
                match = await get_match_info_by_id(match_id)

                if match.info.tournament_code != tournament.code:
                    continue

                # found the tournament match
                logging.info(f"Found tournament match {match_id} for game {game.id}")

                winning_side = await tournament_handler.score_tournament(
                    tournament=tournament, match=match, session=session
                )

                if winning_side is None:
                    logging.error(
                        f"Failed to score tournament match: {match_id}, game: {game.id}"
                    )
                    continue

                # commit changes to database
                session.commit()

                # send game result to server
                try:
                    await tournament_handler.send_server_game_result(
                        game_id=game.id, server_id=server_id, winning_side=winning_side
                    )
                except:
                    # do nothing if there is no queue channel
                    pass

                # break because we found the match
                break
            else:
                logging.info(f"No completed match found for game {game.id}")
