from discord.ext import commands
from discord.ext.commands.core import check
from inhouse_bot.database_orm import session_scope
from inhouse_bot.database_orm import Admin


class AdminGroupOnly(commands.CheckFailure):
    pass


def admin_group_check():
    """
    Decorator function to check if a user is an admin
    """

    def predicate(ctx: commands.Context):
        if ctx.guild is None:
            return False
            
        # If the user is the owner of the server, they are an admin
        if ctx.author.id == ctx.guild.owner_id:
            return True

        return is_admin(id=ctx.author.id, server_id=ctx.guild.id)

    return check(predicate)


def is_admin(id: int, server_id: int) -> bool:
    with session_scope() as session:
        admin = (
            session.query(Admin)
            .filter(Admin.id == id)
            .filter(Admin.server_id == server_id)
        ).one_or_none()

        if admin:
            return True
    raise AdminGroupOnly()
