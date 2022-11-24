import itertools
import math

import trueskill
import inhouse_bot.common_utils.lol_api.tasks as lol
from typing import List
from inhouse_bot.database_orm import Game, GameParticipant
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

    mmr = 0
    for gameparticipant in team:
        print(gameparticipant.player.name)
        summoner = await lol.get_summoner_by_puuid(
            gameparticipant.player.summoner_puuid
        )
        playerRankInfo = await lol.get_summoner_rank_info_by_id(summoner.id)
        if playerRankInfo:
            rankString = playerRankInfo["tier"] + playerRankInfo["rank"]
            value = mmrValues[rankString]
            mmr += value
        else:
            # We assume players without function at a silver level (TODO: Come up with some reasoning on what value this should be)
            mmr += 1400
    print("\n")
    return mmr


async def evaluate_game(game: Game) -> int:
    """
    Returns based on the mmrs of each
    """
    print("Blue Team")
    blueTeamMMR = await get_team_mmr(game.teams.BLUE)
    print("Red Team")
    redTeamMMR = await get_team_mmr(game.teams.RED)

    print("Blue Team MMR", blueTeamMMR)
    print("Red Team MMR", redTeamMMR)
    print("\n")
    return abs(blueTeamMMR - redTeamMMR)
    blue_team_ratings = [
        trueskill.Rating(mu=p.trueskill_mu, sigma=p.trueskill_sigma)
        for p in game.teams.BLUE
    ]
    red_team_ratings = [
        trueskill.Rating(mu=p.trueskill_mu, sigma=p.trueskill_sigma)
        for p in game.teams.RED
    ]

    delta_mu = sum(r.mu for r in blue_team_ratings) - sum(
        r.mu for r in red_team_ratings
    )

    sum_sigma = sum(
        r.sigma**2 for r in itertools.chain(blue_team_ratings, red_team_ratings)
    )

    size = len(blue_team_ratings) + len(red_team_ratings)

    denominator = math.sqrt(size * (trueskill.BETA * trueskill.BETA) + sum_sigma)

    ts = trueskill.global_env()

    return ts.cdf(delta_mu / denominator)
