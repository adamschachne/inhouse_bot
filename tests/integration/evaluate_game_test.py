from inhouse_bot.database_orm import session_scope
from inhouse_bot.database_orm import Player, GameParticipant
from inhouse_bot.matchmaking_logic.evaluate_game import get_team_mmr
from inhouse_bot.common_utils.fields import RoleEnum, SideEnum
from inhouse_bot.common_utils.lol_api.tasks import get_summoner_by_name
import pytest

globalIdValues = 9999


@pytest.mark.asyncio
async def test_get_summoner_by_name_no_rank():

    with session_scope() as session:
        try:
            # fetch an unranked account
            summoner = await get_summoner_by_name("TOAST")

            # Upload to Player table
            player = Player(
                id=globalIdValues,
                server_id=globalIdValues,
                name="TOAST",
                summoner_puuid=f"{summoner.puuid}",
            )
            session.merge(player)
            session.commit()

            # Query for that player just committed
            playerFetched = (
                session.query(Player)
                .filter(Player.server_id == globalIdValues)
                .filter(Player.id == globalIdValues)
                .first()
            )
            assert playerFetched != None
            assert len(playerFetched.summoner_puuid) > 0
            assert playerFetched.name == "TOAST"
        finally:
            # Database cleanup
            session.execute("DELETE FROM PLAYER WHERE name ='TOAST'")


@pytest.mark.asyncio
async def test_get_summoner_by_name_no_rank_returns_unranked_value():

    with session_scope() as session:
        try:
            # fetch an unranked account
            summoner = await get_summoner_by_name("TOAST")

            # Upload to GameParticipant/Player table
            player = Player(
                id=globalIdValues,
                server_id=globalIdValues,
                name="TOAST",
                summoner_puuid=f"{summoner.puuid}",
            )

            gameParticipant = GameParticipant(
                side=SideEnum.BLUE, role=RoleEnum.BOT, player=player
            )

            # Upload to Game table so matchmaking logic can start
            session.execute(
                f"Insert into game (id, start, server_id) VALUES ({globalIdValues}, CURRENT_TIMESTAMP, {globalIdValues})"
            )

            gameParticipant.game_id = globalIdValues
            session.merge(player)
            session.merge(gameParticipant)
            session.commit()

            # Query for all the gameParticipants
            gameParticipantsFetched = (
                session.query(GameParticipant)
                .filter(Player.server_id == globalIdValues)
                .filter(Player.id == globalIdValues)
                .all()
            )
            assert gameParticipantsFetched != None
            assert len(gameParticipantsFetched) == 1
            assert await get_team_mmr(gameParticipantsFetched) == 1400
        finally:
            # Database cleanup
            session.execute("DELETE FROM GAME_PARTICIPANT WHERE game_id = 9999")
            session.execute("DELETE FROM PLAYER WHERE name ='TOAST'")
            session.execute("DELETE FROM GAME WHERE id = 9999")
