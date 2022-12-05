from inhouse_bot.database_orm import Player
from inhouse_bot.database_orm.session.session import Session, session_scope


def get_player(player_id: int, server_id: int) -> Player | None:
    """
    Returns the player with the given id and server id
    """

    with session_scope() as session:
        session.expire_on_commit = False
        player = (
            session.query(Player)
            .select_from(Player)
            .filter(Player.id == player_id)
            .filter(Player.server_id == server_id)
        ).one_or_none()

    return player
