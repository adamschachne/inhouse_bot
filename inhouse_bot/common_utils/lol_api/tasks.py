from typing import List
import statistics

from pyot.core.queue import Queue
from pyot.models import lol
from pyot.core.exceptions import PyotException


async def get_summoner_by_name(summoner_name: str, no_cache: bool = False):
    summoner = lol.Summoner(name=summoner_name)
    if no_cache:       
        # clear the pipeline sources of this token before requesting
        await summoner.metapipeline.delete(await summoner.token())

    return await summoner.get()

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


async def get_provider(callback_url: str):
    provider = (
        await lol.TournamentProvider("americas")
        .body(region="NA", url=callback_url)
        .post()
    )
    return provider.id


async def get_tournament(name: str, provider_id: int):
    tournament = (
        await lol.Tournament("americas").body(name=name, provider_id=provider_id).post()
    )
    return tournament.id


async def get_tournament_codes(
    tournament_id: str,
    map_type: str,
    pick_type: str,
    team_size: int,
    spectator_type: str,
    count: int,
    allowed_summoner_ids: List[str] | None = None,
    metadata: str | None = None,
):
    if allowed_summoner_ids and len(allowed_summoner_ids) < team_size * 2:
        raise Exception("Not enough players to fill teams.")

    code = (
        await lol.TournamentCodes(region="americas")
        .query(tournament_id=tournament_id, count=count)
        .body(
            map_type=map_type,
            pick_type=pick_type,
            team_size=team_size,
            spectator_type=spectator_type,
            allowed_summoner_ids=allowed_summoner_ids,
            metadata=metadata,
        )
        .post()
    )

    return code.codes


async def get_match_info_by_id(match_id: str):
    return await lol.Match(id=match_id).get()


async def get_tournament_match_history(puuid: str, start_timestamp: int):
    return (
        await lol.MatchHistory(puuid=puuid)
        .query(type="tourney", start_time=start_timestamp)
        .get()
    )


async def get_profile_icon_by_id(icon_id: int):
    return await lol.ProfileIcon(id=icon_id).get()
