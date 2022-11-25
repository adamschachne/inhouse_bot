from typing import List
from sqlalchemy import Column, Integer, JSON, String, Boolean
from sqlalchemy.orm import Mapped
from inhouse_bot.database_orm import bot_declarative_base


class Tournament(bot_declarative_base):
    """Represents a single game in a tournament"""

    __tablename__ = "tournament"

    # tournament code for this tournament
    code: Mapped[str] = Column(String, primary_key=True)

    # name of the tournament
    name: Mapped[str] = Column(String, nullable=False)

    # The tournament id from /lol/tournament/v4/tournaments
    id: Mapped[int] = Column(Integer, nullable=False)

    # The provider id from /lol/tournament/v4/providers response
    provider_id: Mapped[int] = Column(Integer, nullable=False)

    # The optional list of summoner ids that are allowed in this game
    allowed_summoner_ids: Mapped[List[str] | None] = Column(JSON, nullable=True)

    # size of each team (default 5v5), Valid values are 1-5.
    team_size: Mapped[int] = Column(Integer, default=5, nullable=False)

    # TOURNAMENT_DRAFT,
    pick_type: Mapped[str] = Column(String, default="TOURNAMENT_DRAFT", nullable=False)

    # Spectator mode for this game (default: LOBBYONLY), options are NONE, LOBBYONLY, ALL
    spectators: Mapped[str] = Column(String, default="LOBBYONLY", nullable=False)

    # SUMMONERS_RIFT, TWISTED_TREELINE, HOWLING_ABYSS
    map: Mapped[str] = Column(String, default="SUMMONERS_RIFT", nullable=False)

    # BR, EUNE, EUW, JP, LAN, LAS, NA, OCE, PBE, RU, TR
    region: Mapped[str] = Column(String, default="NA", nullable=False)

    # Optional string used to denote any custom information about the game.
    metadata: Mapped[String] = Column(String, nullable=True)

    # Whether or not the tournament game has started
    started: Mapped[bool] = Column(Boolean, default=False, nullable=False)

    # The matchId of the game. Only present if the game has started
    match_id: Mapped[String] = Column(String, nullable=True)
