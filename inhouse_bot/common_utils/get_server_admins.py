from typing import List

from inhouse_bot.database_orm import Player, Admin
from inhouse_bot.database_orm.session.session import session_scope


def get_server_admins(server_id: int) -> List[Player]:

    with session_scope() as session:
        session.expire_on_commit = False
        admins = (
            session.query(Player)
            .select_from(Admin)
            .outerjoin(Player, Admin.id == Player.id and Admin.server_id == server_id)
            .filter(Player.server_id == server_id)
        ).all()

    return admins
