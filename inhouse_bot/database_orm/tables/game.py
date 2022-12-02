from dataclasses import dataclass
from typing import Tuple, List
from datetime import datetime

from discord import Embed
from tabulate import tabulate

from sqlalchemy import Column, Integer, DateTime, BigInteger
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.orm.collections import mapped_collection
from sqlalchemy.dialects.postgresql import ENUM
from inhouse_bot.database_orm import bot_declarative_base
from inhouse_bot.database_orm.tables.game_participant import GameParticipant
from inhouse_bot.database_orm.tables.player import Player
from inhouse_bot.common_utils.fields import RoleEnum, SideEnum, roles_list
from inhouse_bot.common_utils.emoji_and_thumbnails import (
    get_role_emoji,
    get_champion_emoji,
    generate_team_opgg,
)


class Game(bot_declarative_base):
    """
    Represents a single inhouse game, currently only supporting LoL and standard roles
    """

    __tablename__ = "game"

    # Auto-incremented ID field
    id: Mapped[int] = Column(Integer, primary_key=True)

    # Game creation date
    start: Mapped[datetime] = Column(DateTime)

    # Server the game was played from
    server_id: Mapped[int] = Column(BigInteger)

    # Pre-game team mmr
    blue_team_mmr: Mapped[int] = Column(BigInteger)
    red_team_mmr: Mapped[int] = Column(BigInteger)

    # Winner, updated at the end of the game
    winner: Mapped[SideEnum | None] = Column(
        ENUM(SideEnum, name="team_enum"), nullable=True
    )

    # ORM relationship to participants in the game, defined as a [team, role] dictionary
    # TODO sqlalchemy2-stubs has a hard time inferring the type
    participants = relationship(  # type: ignore
        GameParticipant,
        collection_class=mapped_collection(
            lambda participant: (participant.side, participant.role)
        ),
        lazy="joined",
        cascade="all, delete-orphan",
    )

    # We define teams only as properties as it should be easier to work with
    @property
    def teams(self):
        from inhouse_bot.dataclasses.Teams import Teams

        return Teams(
            BLUE=[self.participants[SideEnum.BLUE, role] for role in roles_list],  # type: ignore
            RED=[self.participants[SideEnum.RED, role] for role in roles_list],  # type: ignore
        )

    @property
    def player_ids_list(self) -> List[int]:
        return [p.player_id for p in self.participants.values()]  # type: ignore

    @property
    def players_ping(self) -> str:
        return f"||{' '.join([f'<@{discord_id}>' for discord_id in self.player_ids_list])}||\n"

    def __str__(self):
        return tabulate(
            {
                "BLUE": [p.player.name for p in self.teams.BLUE],
                "RED": [p.player.name for p in self.teams.BLUE],
            },
            headers="keys",
        )

    def get_embed(
        self, embed_type: str, validated_players: List[int] = [], bot=None
    ) -> Embed:
        if embed_type == "GAME_FOUND":
            embed = Embed(
                title="📢 Game found 📢",
                description=f"If you are ready to play, press ✅\n"
                "If you cannot play, press ❌\n"
                "The queue will timeout after a few minutes and AFK players will be automatically dropped "
                "from queue",
            )
        elif embed_type == "GAME_ACCEPTED":
            embed = Embed(
                title="📢 Game accepted 📢",
                description=f"Game {self.id} has been validated and added to the database\n"
                f"Once the game has been played, one of the winners can score it with `!won`\n"
                f"If you wish to cancel the game, use `!cancel`",
            )
        else:
            raise ValueError

        # TODO game.get_embed accesses game.participants.player otherwise it will fail.
        # Game at this point will be detached from a session, so maybe assert that the
        # objects are loaded?

        # if we want to fetch server names for these players, change this to an async function
        # and asyncio.gather the async list comprehensions below
        def get_team_embed_value(idx: int, p: GameParticipant):
            return (
                f"{get_role_emoji(roles_list[idx])}"  # We start with the role emoji
                + (  # Then add loading or ✅ if we are looking at a validation embed
                    ""
                    if embed_type != "GAME_FOUND"
                    else f" {get_champion_emoji('loading', bot)}"
                    if p.player_id not in validated_players
                    else " ✅"
                )
                + f" {p.player.name}"  # And finally add the player name
            )

        # Blue team
        embed.add_field(
            name=f"BLUE ({self.blue_team_mmr})",
            value="\n".join(
                get_team_embed_value(idx, p) for idx, p in enumerate(self.teams.BLUE)
            ),
        )

        # Red team
        embed.add_field(
            name=f"RED ({self.red_team_mmr})",
            value="\n".join(
                get_team_embed_value(idx, p) for idx, p in enumerate(self.teams.RED)
            ),
        )
        if embed_type == "GAME_ACCEPTED":
            embed.add_field(
                name="\u200B",
                value="\u200B",
            )
            embed.add_field(
                name="BLUE Team",
                value=f"[OP.GG]({generate_team_opgg(self.teams.BLUE)})",
                inline=True,
            )

            embed.add_field(
                name="RED Team",
                value=f"[OP.GG]({generate_team_opgg(self.teams.RED)})",
                inline=True,
            )

        return embed

    def __init__(self, players: dict[Tuple[SideEnum, RoleEnum], Player]):
        """
        Creates a Game object and its GameParticipant children.

        Args:
            players: [team, role] -> Player dictionary
        """
        # We use local imports to not have circular imports
        from inhouse_bot.database_orm import GameParticipant

        self.start = datetime.now()

        # First, we write down the participants
        self.participants = {
            (team, role): GameParticipant(team, role, players[team, role])  # type: ignore
            for team, role in players
        }

        game_participants = list(self.participants.values())  # type: ignore
        self.server_id = game_participants[0].player_server_id

    async def matchmake_game(self) -> int:
        from inhouse_bot.matchmaking_logic import evaluate_game

        gameInfo = await evaluate_game(self)
        self.blue_team_mmr = gameInfo.blueTeamMMR
        self.red_team_mmr = gameInfo.redTeamMMR

        return gameInfo.teamDifference
