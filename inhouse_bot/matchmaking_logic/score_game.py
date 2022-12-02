from inhouse_bot.database_orm import session_scope
from inhouse_bot.database_orm.session.session import Session
from inhouse_bot.common_utils.get_last_game import get_last_game


def score_game_from_winning_player(
    player_id: int, server_id: int, session: Session | None = None
):
    """
    Scores the last game of the player on the server as a *win*
    """
    if session is None:
        with session_scope() as session:
            return score_game_from_winning_player(player_id, server_id, session)

    game, participant = get_last_game(player_id, server_id, session)

    if game and participant:
        game.winner = participant.side
        session.merge(game)
