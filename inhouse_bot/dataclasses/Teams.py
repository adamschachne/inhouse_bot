from dataclasses import dataclass
from inhouse_bot.database_orm import GameParticipant
from typing import List


@dataclass
class Teams:
    BLUE: List[GameParticipant]
    RED: List[GameParticipant]
