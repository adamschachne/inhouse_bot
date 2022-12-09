from typing import List, MutableMapping
from discord.ext import commands
from discord.ext.commands import ConversionError
from enum import Enum
import rapidfuzz
import lol_id_tools


class RoleEnum(str, Enum):
    TOP = "TOP"
    JGL = "JGL"
    MID = "MID"
    BOT = "BOT"
    SUP = "SUP"

    def __str__(self):
        return self.value


roles_list = [
    RoleEnum.TOP,
    RoleEnum.JGL,
    RoleEnum.MID,
    RoleEnum.BOT,
    RoleEnum.SUP,
]


class SideEnum(str, Enum):
    BLUE = "BLUE"
    RED = "RED"

    def __str__(self):
        return self.value


foreignkey_cascade_options: MutableMapping = {
    "onupdate": "CASCADE",
    "ondelete": "CASCADE",
}

# This is a dict used for fuzzy matching
full_roles_dict = {
    "top": "TOP",
    "jgl": "JGL",
    "jungle": "JGL",
    "jungler": "JGL",
    "mid": "MID",
    "bot": "BOT",
    "adc": "BOT",
    "sup": "SUP",
    "supp": "SUP",
    "support": "SUP",
}


class RoleConverter(commands.Converter):
    async def convert(self, ctx, argument):
        """
        Converts an input string to a clean role
        """

        matched_string, ratio, _ = rapidfuzz.process.extractOne(
            argument, list(full_roles_dict.keys())
        )
        if ratio < 85:
            await ctx.send(f"The role was not understood")
            raise ConversionError(self, Exception("Role not understood"))
        else:
            return full_roles_dict[matched_string]


class QueueRoleConverter(RoleConverter):
    async def convert(self, ctx, argument):
        if str.upper(argument) == "ALL":
            return "ALL"
        return await super().convert(ctx, argument)


class ChampionNameConverter(commands.Converter):
    async def convert(self, ctx, argument):
        """
        Converts an input string to a clean champion ID
        """
        try:
            return lol_id_tools.get_id(
                argument, input_locale="en_US", object_type="champion"
            )

        except lol_id_tools.NoMatchingNameFound:
            await ctx.send(f"The champion name was not understood")
            raise ConversionError(self, Exception("Champion name not understood"))
