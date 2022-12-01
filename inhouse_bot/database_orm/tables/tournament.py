from typing import List
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, relationship
from inhouse_bot.database_orm import bot_declarative_base
from inhouse_bot.database_orm.tables.game import Game
from inhouse_bot.common_utils.fields import foreignkey_cascade_options


class Tournament(bot_declarative_base):
    """Represents a single game in a tournament"""

    __tablename__ = "tournament_code"

    # tournament code for this tournament
    code: Mapped[str] = Column(String, primary_key=True)

    # name of the tournament
    name: Mapped[str] = Column(String, nullable=False)

    # The tournament id from /lol/tournament/v4/tournaments
    tournament_id: Mapped[int] = Column(Integer, nullable=False)

    # The provider id from /lol/tournament/v4/providers response
    provider_id: Mapped[int] = Column(Integer, nullable=False)

    # The optional list of summoner ids that are allowed in this game
    allowed_summoner_ids: Mapped[List[str] | None] = Column(
        ARRAY(String, as_tuple=False, dimensions=1), nullable=True
    )

    # size of each team (default 5v5), Valid values are 1-5.
    team_size: Mapped[int] = Column(Integer, default=5, nullable=False)

    # TOURNAMENT_DRAFT,
    pick_type: Mapped[str] = Column(String, default="TOURNAMENT_DRAFT", nullable=False)

    # Spectator mode for this game (default: LOBBYONLY), options are NONE, LOBBYONLY, ALL
    spectator_type: Mapped[str] = Column(String, default="LOBBYONLY", nullable=False)

    # SUMMONERS_RIFT, TWISTED_TREELINE, HOWLING_ABYSS
    map_type: Mapped[str] = Column(String, default="SUMMONERS_RIFT", nullable=False)

    # BR, EUNE, EUW, JP, LAN, LAS, NA, OCE, PBE, RU, TR
    region: Mapped[str] = Column(String, default="NA", nullable=False)

    # Optional string used to denote any custom information about the game.
    tournament_metadata: Mapped[str] = Column(String, nullable=True)

    # The match id of the game.
    match_id: Mapped[str] = Column(String, nullable=True)

    # The Game for this tournament
    game_id: Mapped[int] = Column(
        Integer, ForeignKey(Game.id, **foreignkey_cascade_options), nullable=False
    )
    game: Mapped[Game] = relationship(Game, uselist=False)
