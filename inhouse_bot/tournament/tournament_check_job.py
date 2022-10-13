from discord.ext import commands
from typing import Optional


async def tournament_check(bot: commands.Bot, server_id: Optional[int]):
    """
    Tournaments API background job. This looks at the active tournament matches
    and check for status updates on them.
    """
    # TODO check tournament job
    # with session_scope() as session:
