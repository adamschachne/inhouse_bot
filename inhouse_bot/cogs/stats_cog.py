from pydoc import describe
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta

import dateparser
import discord
import lol_id_tools
import mplcyberpunk
import sqlalchemy

from discord import Embed
from discord.ext import commands, menus
from discord.ext.commands import guild_only

import matplotlib
import matplotlib.pyplot as plt
import inhouse_bot.common_utils.lol_api.tasks as lol
from inhouse_bot.common_utils.constants import PREFIX
from inhouse_bot.common_utils.docstring import doc
from inhouse_bot.common_utils.stats_helper import (
    get_player_stats,
    get_player_history,
    get_roles_most_used_champs,
)
from inhouse_bot.common_utils.emoji_and_thumbnails import get_role_emoji, get_rank_emoji
from inhouse_bot.database_orm import (
    session_scope,
    GameParticipant,
    Game,
    PlayerRating,
    Player,
)
from inhouse_bot.common_utils.fields import ChampionNameConverter, RoleConverter
from inhouse_bot.common_utils.get_last_game import get_last_game

from inhouse_bot.inhouse_bot import InhouseBot
from inhouse_bot.ranking_channel_handler.ranking_channel_handler import (
    ranking_channel_handler,
)
from inhouse_bot.stats_menus.history_pages import HistoryPagesSource
from inhouse_bot.stats_menus.ranking_pages import RankingPagesSource


matplotlib.use("Agg")
plt.style.use("cyberpunk")


class StatsCog(commands.Cog, name="Stats"):
    """
    Display game-related statistics
    """

    def __init__(self, bot: InhouseBot):
        self.bot = bot

    @commands.command()
    @guild_only()
    @doc(
        f"""
        Saves the champion you used in your last game

        Older games can be filled with {PREFIX}champion champion_name game_id
        You can find the ID of the games you played with {PREFIX}history

        Example:
            {PREFIX}champion riven
            {PREFIX}champion riven 1
    """
    )
    async def champion(
        self,
        ctx: commands.Context,
        champion_name: ChampionNameConverter(),
        game_id: int = None,
    ):
        with session_scope() as session:
            if not game_id:
                game, participant = get_last_game(
                    player_id=ctx.author.id, server_id=ctx.guild.id, session=session
                )
            else:
                game, participant = (
                    session.query(Game, GameParticipant)
                    .select_from(Game)
                    .join(GameParticipant)
                    .filter(Game.id == game_id)
                    .filter(GameParticipant.player_id == ctx.author.id)
                ).one_or_none()

            # We write down the champion
            participant.champion_id = champion_name

            game_id = game.id

        await ctx.send(
            f"Champion for game {game_id} was set to "
            f"{lol_id_tools.get_name(champion_name, object_type='champion')} for {ctx.author.display_name}"
        )

    @commands.command(aliases=["match_history", "mh"])
    @doc(
        f"""
        Displays your games history

        Example:
            {PREFIX}history
    """
    )
    async def history(self, ctx: commands.Context):
        # TODO LOW PRIO Add an @ user for admins

        game_participant_list = await get_player_history(ctx.author.id, ctx.guild.id)
        if not game_participant_list:
            await ctx.send("No games found")
            return

        pages = menus.MenuPages(
            source=HistoryPagesSource(
                game_participant_list,
                self.bot,
                player_name=ctx.author.display_name,
                is_dms=True if not ctx.guild else False,
            ),
            clear_reactions_after=True,
        )
        await pages.start(ctx)

    @commands.command(aliases=["rankings"])
    @guild_only()
    @doc(
        f"""
        Displays the top players on the server

        A role can be supplied to only display the ranking for this role

        Example:
            {PREFIX}ranking
            {PREFIX}ranking mid
    """
    )
    async def ranking(self, ctx: commands.Context, role: RoleConverter() = None):
        ratings = ranking_channel_handler.get_server_ratings(ctx.guild.id, role=role)

        if not ratings:
            await ctx.send("No games played yet")
            return

        pages = menus.MenuPages(
            source=RankingPagesSource(
                ratings,
                embed_name_suffix=f"on {ctx.guild.name}{f' - {get_role_emoji(role)}' if role else ''}",
            ),
            clear_reactions_after=True,
        )
        await pages.start(ctx)

    @commands.command(aliases=["rating_history", "ratings_history"])
    async def mmr_history(self, ctx: commands.Context):
        """
        Displays a graph of your MMR history over the past month
        """
        date_start = datetime.now() - timedelta(hours=24 * 30)

        with session_scope() as session:

            participants = (
                session.query(
                    Game.start,
                    GameParticipant.role,
                    GameParticipant.mmr,
                    PlayerRating.mmr.label("latest_mmr"),
                )
                .select_from(Game)
                .join(GameParticipant)
                .join(PlayerRating)  # Join on rating first to select the right role
                .join(Player)
                .filter(GameParticipant.player_id == ctx.author.id)
                .filter(Game.start > date_start)
                .order_by(Game.start.asc())
            )

        mmr_history = defaultdict(lambda: {"dates": [], "mmr": []})

        latest_role_mmr = {}

        for row in participants:
            mmr_history[row.role]["dates"].append(row.start)
            mmr_history[row.role]["mmr"].append(row.mmr)

            latest_role_mmr[row.role] = row.latest_mmr

        legend = []
        for role in mmr_history:
            # We add a data point at the current timestamp with the player’s current MMR
            mmr_history[role]["dates"].append(datetime.now())
            mmr_history[role]["mmr"].append(latest_role_mmr[role])

            plt.plot(mmr_history[role]["dates"], mmr_history[role]["mmr"])
            legend.append(role)

        plt.legend(legend)
        plt.title(f"MMR variation in the last month for {ctx.author.display_name}")
        mplcyberpunk.add_glow_effects()

        # This looks to be unnecessary verbose with all the closing by hand, I should take a look
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
            plt.savefig(temp.name)
            file = discord.File(temp.name, filename=temp.name)
            await ctx.send(file=file)
            plt.close()
            temp.close()

    # TODO MEDIUM PRIO (simple) Add !champions_stats once again!!!

    @commands.command(aliases=["scout", "profile"])
    @guild_only()
    @doc(
        f"""
        Displays information about a player and champs used in inhouses
        Example:
            {PREFIX}scout @User
            {PREFIX}profile @User
    """
    )
    async def scouting(self, ctx: commands.Context, name_arg: str):
        with session_scope() as session:
            player = (
                session.query(Player)
                .select_from(Player)
                .filter(Player.server_id == ctx.guild.id)
                .filter(Player.name.ilike(f"%{name_arg}%"))
            ).one_or_none()

            if not player:
                await ctx.send("This player has no games recorded.")
                return

            # #### Create the initial embed object ####

            # All Users default to unverified until further data is processed
            embed = discord.Embed()
            file = discord.File("riot-ranks/UNVERIFIED.png")
            embed.set_thumbnail(url="attachment://UNVERIFIED.png")

            if player.summoner_puuid:
                summoner = await lol.get_summoner_by_puuid(player.summoner_puuid)
                playerRankInfo = await lol.get_summoner_rank_info_by_id(summoner.id)
                embed.title = f"{summoner.name} - OP.GG"

                # Accounting for names with spaces
                embed.url = f"https://www.op.gg/summoners/na/{summoner.name}".replace(
                    " ", ""
                )

                # If a player has a rank whether it being (Solo/Duo or Flex)
                if playerRankInfo:
                    embed.set_author(name=f"Rank: {playerRankInfo['tier']}")
                    file = discord.File(
                        f"riot-ranks/{playerRankInfo['tier']}.png",
                        filename=f"{playerRankInfo['tier']}.png",
                    )
                    embed.set_thumbnail(
                        url=f"attachment://{playerRankInfo['tier']}.png"
                    )

                else:
                    embed.set_author(name=f"Rank: UNRANKED")
                    file = discord.File(
                        "riot-ranks/UNRANKED.png", filename="UNRANKED.png"
                    )
                    embed.set_thumbnail(url="attachment://UNRANKED.png")

            player_stats = await get_player_stats(player.id, player.server_id)
            embed.add_field(
                name="Role Stats", value="\n".join(player_stats), inline=False
            )

            champs_used_stats = await get_roles_most_used_champs(
                player.id, player.server_id
            )
            embed.add_field(
                name="Most Used Champs",
                value="\n".join(champs_used_stats),
                inline=False,
            )

            embed.set_footer(text=f"Scouting information about: {player.name}")
            await ctx.send(file=file, embed=embed)
