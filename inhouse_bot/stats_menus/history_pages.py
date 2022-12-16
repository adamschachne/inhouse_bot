from collections import Counter
from typing import Tuple, List

from discord import Embed
from discord.ext import menus, commands
from inhouse_bot.common_utils.emoji_and_thumbnails import (
    get_champion_emoji,
    get_role_emoji,
    role_thumbnail_dict,
)
from inhouse_bot.common_utils.fields import RoleEnum
from inhouse_bot.database_orm import GameParticipant, Game

entries_type = List[Tuple[Game, GameParticipant]]


class HistoryPagesSource(menus.ListPageSource):
    def __init__(
        self, entries: entries_type, bot: commands.Bot, author_name: str, is_dms=False
    ):
        self.bot = bot
        self.author_name = author_name
        self.is_dms = is_dms
        super().__init__(entries, per_page=10)

    async def format_page(self, menu: menus.MenuPages, entries: entries_type):
        embed = Embed()

        embed.set_footer(
            text=f"Page {menu.current_page + 1} of {self._max_pages} "
            f"| Use !champion [name] [game_id] to save champions"
        )

        rows = []
        role_counter: Counter[RoleEnum] = Counter()

        max_game_id_length = max(len(str(game.id)) for game, participant in entries)

        name: str | None = None

        for game, participant in entries:
            name = participant.player.name
            champion_emoji = get_champion_emoji(participant.champion_id, self.bot)
            role = get_role_emoji(participant.role)
            server = self.bot.get_guild(game.server_id)
            server_name = server.name if server else ""

            role_counter[participant.role] += 1

            if not game.winner:
                result = "⚔"
            elif game.winner == participant.side:
                result = "✅"
            else:
                result = "❌"

            id_padding = max_game_id_length - len(str(game.id)) + 2

            # TODO LOW PRIO add pre-game MMR
            output_string = (
                f"{result}   {role}   {champion_emoji}  "
                f"`#{game.id}{' '*id_padding}{game.start.date()}"
                + ("`" if not self.is_dms else f"  {server_name}`")
            )

            rows.append(output_string)

        embed.set_thumbnail(url=role_thumbnail_dict[role_counter.most_common(1)[0][0]])

        embed.add_field(
            name=f"{name or self.author_name}’s match history", value="\n".join(rows)
        )

        return embed
