from typing import List
from pydantic import BaseModel


class TournamentCodeParams(BaseModel):
    allowedSummonerIds: List[str]
    mapType: str
    metadata: str
    pickType: str
    spectatorType: str
    teamSize: int
