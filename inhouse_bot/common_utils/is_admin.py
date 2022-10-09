from http import server
from discord.ext import commands
from discord.ext.commands.core import check
from inhouse_bot.database_orm import session_scope
from inhouse_bot.database_orm import Admin


def admin_group_check():
    """
    Decorator function to check if a user is an admin
    """
    def predicate(ctx: commands.Context):
        return is_admin(id=ctx.author.id, server_id=ctx.guild.id)
    return check(predicate)

def is_admin(id: int, server_id: str) -> bool:
    with session_scope() as session:
        admin = (
            session.query(Admin)
            .filter(Admin.id == id)
            .filter(Admin.server_id == server_id)
        ).one_or_none()
        
        if admin:
            return True
    return False
