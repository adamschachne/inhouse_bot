from dataclasses import dataclass


@dataclass
class GameInfo:
    blueTeamMMR: int
    redTeamMMR: int
    teamDifference: int
