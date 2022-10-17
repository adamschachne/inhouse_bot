from typing import Optional, Tuple

from sqlalchemy import desc

from inhouse_bot.database_orm import Game, GameParticipant
from inhouse_bot.database_orm.session.session import Session


def get_last_game(
    player_id: int, server_id: int, session: Session
) -> Tuple[Optional[Game], Optional[GameParticipant]]:
    return (
        session.query(Game, GameParticipant)
        .select_from(Game)
        .join(GameParticipant)
        .filter(Game.server_id == server_id)
        .filter(GameParticipant.player_id == player_id)
        .order_by(desc(Game.start))
    ).first() or (
        None,
        None,
    )  # To not have unpacking errors
