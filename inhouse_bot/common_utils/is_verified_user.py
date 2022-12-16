from discord.ext import commands
from typing import List
from inhouse_bot.common_utils.constants import PREFIX
from inhouse_bot.database_orm import session_scope
from inhouse_bot.database_orm import Player


async def are_verified_users(
    ctx: commands.Context, ids: List[int], server_id: int
) -> bool:
    with session_scope() as session:
        for id in ids:
            player: Player | None = (
                session.query(Player)
                .filter(Player.id == id)
                .filter(Player.server_id == server_id)
            ).one_or_none()

            # If player doesn't exist or isn't verified
            if not player or not player.is_verified:
                await ctx.send(
                    f"<@{id}> must get verified to queue. Use {PREFIX}verify <summoner name> to get verified."
                )
                return False

        return True
