from typing import List
import statistics

from pyot.core.queue import Queue
from pyot.models import lol
from pyot.core.exceptions import PyotException


async def get_summoner_by_name(summoner_name: str):
    return await lol.Summoner(name=summoner_name).get()


async def average_win_rate_10_matches(summoner_name: str):
    async with Queue() as queue:
        summoner = await lol.Summoner(name=summoner_name).get()
        history = await summoner.match_history.get()
        for match in history.matches[:10]:
            await queue.put(match.get())
        first_10_matches: List[lol.Match] = await queue.join()
    wins = []
    for match in first_10_matches:
        for participant in match.info.participants:
            if participant.puuid == summoner.puuid:
                wins.append(int(participant.win))
    return statistics.mean(wins or [0])


async def get_summoner_by_puuid(puuid: str):
    summoner = await lol.Summoner(puuid=puuid).get()
    return summoner


async def get_summoner_rank_info_by_id(summoner_id: str):
    summoner = await lol.SummonerLeague(summoner_id=summoner_id).get()

    # Prioritize -- Solo/Duo -> Flex -> TFT Rank
    for entry in summoner._meta.data["entries"]:
        if entry["queueType"] == "RANKED_SOLO_5x5":
            return entry

    for entry in summoner._meta.data["entries"]:
        if entry["queueType"] == "RANKED_FLEX_SR":
            return entry

    return []


async def create_provider(callback_url: str):
    provider = (
        await lol.TournamentProvider("americas")
        .body(region="NA", url=callback_url)
        .post()
    )
    return provider.id
