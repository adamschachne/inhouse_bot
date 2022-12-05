from inhouse_bot.database_orm.tables.player import Player
from inhouse_bot.database_orm import session_scope


def set_player_summoner(
    server_id: int, user_id: int, summoner_puuid: str, summoner_name: str
):
    """
    Sets the summoner puuid and name for a player. If the summoner is already set for another player,
    the summoner is removed from that player and set for the new player. If the summoner is already
    set for the player, this function does nothing
    """
    with session_scope() as session:
        player = (
            session.query(Player)
            .select_from(Player)
            .filter(Player.server_id == server_id)
            .filter(Player.summoner_puuid == summoner_puuid)
        ).one_or_none()

        if player:
            if player.id == user_id:
                # Player is already verified => do nothing
                return
            else:
                # case when there is already a player with this name -> clear player's name and puuid
                (
                    session.query(Player)
                    .filter(Player.id == player.id)
                    .filter(Player.server_id == server_id)
                    .update({Player.summoner_puuid: None, Player.name: None})
                )

        # save the new player's summoner name
        session.merge(
            Player(
                id=user_id,
                server_id=server_id,
                name=summoner_name,
                summoner_puuid=summoner_puuid,
            )
        )
