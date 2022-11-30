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
