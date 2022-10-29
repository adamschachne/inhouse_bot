from sqlalchemy import (
    BigInteger,
    Column,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped

from inhouse_bot.common_utils.fields import (
    RoleEnum,
    SideEnum,
    foreignkey_cascade_options,
)

from sqlalchemy.dialects.postgresql import ENUM
from inhouse_bot.database_orm import bot_declarative_base
from inhouse_bot.database_orm.tables.player import Player
from inhouse_bot.database_orm.tables.player_rating import PlayerRating


class GameParticipant(bot_declarative_base):
    """Represents a participant in an inhouse game"""

    __tablename__ = "game_participant"

    # Reference to the game table
    game_id: Mapped[int] = Column(
        Integer, ForeignKey("game.id", **foreignkey_cascade_options), primary_key=True
    )

    # Identifier among game participants
    side: Mapped[SideEnum] = Column(ENUM(SideEnum, name="team_enum"), primary_key=True)
    role: Mapped[RoleEnum] = Column(ENUM(RoleEnum, name="role_enum"), primary_key=True)

    # Unique player_id and server_id, which heavily simplifies joining to Player
    player_id: Mapped[int] = Column(BigInteger)
    player_server_id: Mapped[int] = Column(BigInteger)

    # Player & Player Rating relationship
    player: Mapped[Player] = relationship(Player, lazy="joined", uselist=False)

    player_rating: Mapped[PlayerRating] = relationship(
        PlayerRating,
        viewonly=True,
    )

    # Champion id, only filled if the player updates it by themselves after the game
    champion_id: Mapped[int | None] = Column(Integer)

    # Pre-game TrueSkill values
    trueskill_mu: Mapped[float] = Column(Float)
    trueskill_sigma: Mapped[float] = Column(Float)

    # Foreign key to Player
    __table_args__ = (
        ForeignKeyConstraint(
            (player_id, player_server_id), (Player.id, Player.server_id)
        ),
        ForeignKeyConstraint(
            (player_id, player_server_id, role),
            (PlayerRating.player_id, PlayerRating.player_server_id, PlayerRating.role),
        ),
    )

    # Conservative rating for MMR display
    @hybrid_property
    def mmr(self):
        return 20 * (self.trueskill_mu - 3 * self.trueskill_sigma + 25)

    # Called only from the Game constructor itself
    def __init__(self, side: SideEnum, role: RoleEnum, player: Player):
        self.side = side
        self.role = role

        self.player = player
        self.player_id = player.id
        self.player_server_id = player.server_id

        self.trueskill_mu = player.ratings[role].trueskill_mu
        self.trueskill_sigma = player.ratings[role].trueskill_sigma
