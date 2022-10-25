from typing import List, Tuple
from inhouse_bot.database_orm import (
    session_scope,
    GameParticipant,
    Game,
    PlayerRating,
    Player,
)
import sqlalchemy
from inhouse_bot.common_utils.emoji_and_thumbnails import (
    get_role_emoji,
    get_rank_emoji,
    get_champion_name_by_id,
)
from discord.ext import commands
from inhouse_bot.common_utils.fields import RoleEnum, roles_list


async def get_player_stats(player_id, server_id):
    with session_scope() as session:
        rating_objects = (
            session.query(
                PlayerRating,
                sqlalchemy.func.count().label("count"),
                (
                    sqlalchemy.func.sum(
                        (Game.winner == GameParticipant.side).cast(sqlalchemy.Integer)
                    )
                ).label("wins"),
            )
            .select_from(PlayerRating)
            .join(GameParticipant)
            .join(Game)
            .filter(PlayerRating.player_id == player_id)
            .group_by(PlayerRating)
        )

        if server_id:
            rating_objects = rating_objects.filter(
                PlayerRating.player_server_id == server_id
            )

        rows = []
        for row in sorted(rating_objects.all(), key=lambda r: -r.count):
            # TODO LOW PRIO Make that a subquery
            rank = (
                session.query(sqlalchemy.func.count())
                .select_from(PlayerRating)
                .filter(PlayerRating.player_server_id == server_id)
                .filter(PlayerRating.role == row.PlayerRating.role)
                .filter(PlayerRating.mmr > row.PlayerRating.mmr)
            ).first()[0]

            rank_str = get_rank_emoji(rank)

            row_string = (
                f"{rank_str}",
                f"{get_role_emoji(row.PlayerRating.role)}",
                f"{int(row.PlayerRating.mmr)} MMR",
                f"{row.wins}W {row.count-row.wins}L",
                f"{round(row.wins/row.count, 2) * 100}% WR",
            )
            rows.append("  | ".join(row_string))

        if not rows:
            return [("Player has no games played yet.")]

        return rows


async def get_player_history(
    player_id, server_id
) -> List[Tuple[Game, GameParticipant]]:
    with session_scope() as session:
        session.expire_on_commit = False

        game_participant_query = (
            session.query(Game, GameParticipant)
            .select_from(Game)
            .join(GameParticipant)
            .filter(GameParticipant.player_id == player_id)
            .order_by(Game.start.desc())
        )

        # If we’re on a server, we only show games played on that server
        if server_id:
            game_participant_query = game_participant_query.filter(
                Game.server_id == server_id
            )

        game_participant_list = game_participant_query.limit(100).all()

        return game_participant_list


async def get_roles_most_used_champs(player_id, server_id):
    game_participant_list = await get_player_history(player_id, server_id)
    if not game_participant_list:
        return [("No champions are registered for player.")]

    roleChampDict = {key: {} for key in RoleEnum}

    # Keeping track of all the champs used for each role
    for game_participant in game_participant_list:
        if game_participant[1].champion_id:
            championId = game_participant[1].champion_id
            role = game_participant[1].role
            occurencyMap = roleChampDict[role]
            if championId not in occurencyMap:
                occurencyMap[championId] = 1
            else:
                occurencyMap[championId] += 1

    rows = []
    # Sort map of champs for each role and get the top 3
    for role in roles_list:
        row_string = ()
        champs_collection = []

        most_played = sorted(
            roleChampDict[role].items(), key=lambda item: item[1], reverse=True
        )[0:3]

        for key, value in most_played:
            champs_collection.append(get_champion_name_by_id(key) + f" ({value})")

        if champs_collection:
            row_string = row_string + (
                f"{get_role_emoji(role)}: {', '.join(champs_collection)}",
            )
        else:
            row_string = row_string + (f"{get_role_emoji(role)}: No Role Data.",)

        rows.append("  | ".join(row_string))

    return rows
