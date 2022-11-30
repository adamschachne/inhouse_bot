import inhouse_bot.common_utils.lol_api.tasks as lol
from typing import List
from inhouse_bot.database_orm import Game, GameParticipant
from inhouse_bot.dataclasses import GameInfo
from sqlalchemy import BigInteger


async def get_team_mmr(team: List[GameParticipant]) -> int:
    mmrValues = {
        "IRONIV": 200,
        "IRONIII": 400,
        "IRONII": 800,
        "IRONI": 1000,
        "BRONZEIV": 1100,
        "BRONZEIII": 1150,
        "BRONZEII": 1250,
        "BRONZEI": 1300,
        "SILVERIV": 1400,
        "SILVERIII": 1450,
        "SILVERII": 1550,
        "SILVERI": 1600,
        "GOLDIV": 1700,
        "GOLDIII": 1750,
        "GOLDII": 1850,
        "GOLDI": 1900,
        "PLATINUMIV": 2000,
        "PLATINUMIII": 2050,
        "PLATINUMII": 2150,
        "PLATINUMI": 2200,
        "DIAMONDIV": 2300,
        "DIAMONDIII": 2350,
        "DIAMONDII": 2450,
        "DIAMONDI": 2500,
        "MASTERI": 2750,
        "GRANDMASTERI": 3000,
        "CHALLENGERI": 3250,
    }
    # TODO: Log this functions data to see it returns succesfully

    mmr = 0
    for gameparticipant in team:
        summoner = await lol.get_summoner_by_puuid(
            str(gameparticipant.player.summoner_puuid)
        )
        playerRankInfo = await lol.get_summoner_rank_info_by_id(summoner.id)
        if playerRankInfo:
            rankString = playerRankInfo["tier"] + playerRankInfo["rank"]
            value = mmrValues[rankString]
            mmr += value
        else:
            # We assume players without rank play at a silver level
            # (TODO: Silver 4 can still be too high for unranked players, consider going to bronze/iron if matchmaking is really bad)
            mmr += mmrValues["SILVERIV"]
    return mmr


async def evaluate_game(game: Game) -> GameInfo:
    """
    Returns based on the mmrs of each
    """
    # TODO: Log this functions data to see it returns succesfully
    blueTeamMMR = await get_team_mmr(game.teams.BLUE)
    redTeamMMR = await get_team_mmr(game.teams.RED)

    gameInfoObj = GameInfo(blueTeamMMR, redTeamMMR, abs(blueTeamMMR - redTeamMMR))
    return gameInfoObj
