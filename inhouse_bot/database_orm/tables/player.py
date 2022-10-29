from sqlalchemy import Column, String, BigInteger, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.orm.collections import attribute_mapped_collection
from inhouse_bot.common_utils.fields import RoleEnum
from inhouse_bot.database_orm import bot_declarative_base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inhouse_bot.database_orm.tables.player_rating import PlayerRating


class Player(bot_declarative_base):
    """Represents a player taking part in inhouse games"""

    __tablename__ = "player"
    __table_args__ = (
        UniqueConstraint(
            "server_id", "summoner_puuid", name="unique_server_id_summoner_puuid"
        ),
    )

    # Discord account info
    id: Mapped[int] = Column(BigInteger, primary_key=True)

    # One player object per server_id
    server_id: Mapped[int] = Column(BigInteger, primary_key=True)

    # Last known Summoner name or Discord name of this player
    name: Mapped[str] = Column(String, nullable=False)

    # Player team as defined by themselves
    team: Mapped[str | None] = Column(String)

    # Summoner puuid
    summoner_puuid: Mapped[str | None] = Column(String)

    # We automatically load the ratings when loading a Player object
    ratings: Mapped[dict[RoleEnum, "PlayerRating"]] = relationship(
        "PlayerRating",
        collection_class=attribute_mapped_collection("role"),
        backref="player",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<Player: {self.id=} | {self.name=}>"

    async def get_summoner_name(self):
        from inhouse_bot.common_utils.lol_api.tasks import (
            get_summoner_by_puuid,
            PyotException,
        )

        try:
            if self.summoner_puuid:
                summoner = await get_summoner_by_puuid(self.summoner_puuid)
                self.name = summoner.name
                return summoner.name
        except PyotException as ex:
            # TODO use logger
            print(f"Error getting summoner name: {ex}")

        return self.name
