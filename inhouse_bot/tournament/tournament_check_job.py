import logging
from discord.ext import commands
from typing import Optional

from inhouse_bot.database_orm import session_scope


async def tournament_check(bot: commands.Bot, server_id: Optional[int]):
    """
    Tournaments API background job. This looks at the active tournament matches
    and check for status updates on them.
    """

    logging.info("Checking for completed matches")
    # with session_scope() as session:

    # TODO query for tournaments whose games do not have a winner
    # get the first player from those games, search their matches for a completed match with a tournament_code
    # matching the tournament_code of the tournament
    # => if found, update the game with the winner
