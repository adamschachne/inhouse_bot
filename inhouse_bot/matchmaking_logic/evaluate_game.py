import inhouse_bot.common_utils.lol_api.tasks as lol
from typing import List, Dict
from inhouse_bot.database_orm import Game, GameParticipant
from inhouse_bot.dataclasses.GameInfo import GameInfo
from sqlalchemy import BigInteger
import logging
from inhouse_bot.common_utils.fields import SideEnum, RoleEnum


async def find_team_and_lane_mmr(team: List[GameParticipant]) -> GameInfo:
    """
    1. Sum the MMR each team
    2. Compare the MMR of each player and their lane opponent
    3. Attempt to find the smallest possible difference among MMR
    """

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

    laneMMR = {(side, role): 0 for side in SideEnum for role in RoleEnum}

    blueTeamMMR = 0
    redTeamMMR = 0
    for gameparticipant in team:
        summoner = await lol.get_summoner_by_puuid(
            str(gameparticipant.player.summoner_puuid)
        )
        playerRankInfo = await lol.get_summoner_rank_info_by_id(summoner.id)

        if playerRankInfo:
            rankString = playerRankInfo["tier"] + playerRankInfo["rank"]
            value = mmrValues[rankString]
        else:
            value = mmrValues["BRONZEI"]

        if gameparticipant.side == SideEnum.BLUE:
            blueTeamMMR += value

        elif gameparticipant.side == SideEnum.RED:
            redTeamMMR += value

        # Storing each players lane mmr
        laneMMR[(gameparticipant.side, gameparticipant.role)] = value

    teamMMR = abs(blueTeamMMR - redTeamMMR)
    teamMMRWithLane = teamMMR + get_lane_differential(laneMMR)

    logging.info(
        f"Blue Team: {blueTeamMMR} | Red Team: {redTeamMMR} | TeamMMRDifferenceWithLane: {teamMMRWithLane}"
    )
    return GameInfo(blueTeamMMR, redTeamMMR, teamMMRWithLane)


def get_lane_differential(laneMMR: Dict[str, int]) -> int:
    """
    1. Get each players opponent and attempt to put players of equal level against each other, if they queue for the same role
    """
    topDiff = abs(
        laneMMR[(SideEnum.BLUE, RoleEnum.TOP)] - laneMMR[(SideEnum.RED, RoleEnum.TOP)]
    )

    jgDiff = abs(
        laneMMR[(SideEnum.BLUE, RoleEnum.JGL)] - laneMMR[(SideEnum.RED, RoleEnum.JGL)]
    )

    midDiff = abs(
        laneMMR[(SideEnum.BLUE, RoleEnum.MID)] - laneMMR[(SideEnum.RED, RoleEnum.MID)]
    )

    botDiff = abs(
        laneMMR[(SideEnum.BLUE, RoleEnum.BOT)] - laneMMR[(SideEnum.RED, RoleEnum.BOT)]
    )

    suppDiff = abs(
        laneMMR[(SideEnum.BLUE, RoleEnum.SUP)] - laneMMR[(SideEnum.RED, RoleEnum.SUP)]
    )
    return topDiff + jgDiff + midDiff + botDiff + suppDiff


async def evaluate_game(game: Game) -> GameInfo:

    teamsList = []
    teamsList.extend(game.teams.BLUE)
    teamsList.extend(game.teams.RED)

    return await find_team_and_lane_mmr(teamsList)
