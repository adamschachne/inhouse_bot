from typing import Dict, List
from pydantic import BaseModel


class GameResultParams(BaseModel):
    startTime: int
    winningTeam: List[Dict]
    losingTeam: List[Dict]
    shortCode: str
    gameId: int
    gameName: str
    gameType: str
    gameMap: int
    gameMode: str
    region: str
    metaData: str | None = None
