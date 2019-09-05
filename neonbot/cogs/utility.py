import os
import random
from time import time

import psutil
from addict import Dict
from aiohttp import ClientSession
from discord.ext import commands

from .. import __author__, __title__, __version__, bot
from ..helpers.date import format_seconds
from ..helpers.utils import Embed


async def chatbot(user_id, message):
    res = await bot.session.get(
        "https://program-o.com/v3/chat.php", params={"say": message}
    )
    return Dict(await res.json())


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def random(self, ctx, *args):
        await ctx.send(embed=Embed(random.choice(args)))

    @commands.command(aliases=["stats"])
    async def status(self, ctx):
        from .event import commands_executed

        process = psutil.Process(os.getpid())

        embed = Embed()
        embed.set_author(
            name=f"{__title__} v{__version__}", icon_url=self.bot.user.avatar_url
        )
        embed.add_field(name="Username", value=self.bot.user.name)
        embed.add_field(
            name="Created On", value=f"{self.bot.user.created_at:%Y-%m-%d %I:%M:%S %p}"
        )
        embed.add_field(name="Created By", value=__author__)
        embed.add_field(name="Guilds", value=len(self.bot.guilds))
        embed.add_field(
            name="Channels", value=sum(1 for _ in self.bot.get_all_channels())
        )
        embed.add_field(name="Users", value=len(self.bot.users))
        embed.add_field(name="Commands Executed", value=commands_executed)
        embed.add_field(
            name="Ram Usage",
            value=f"Approximately {(process.memory_info().rss / 1024000):.2f} MB",
            inline=True,
        )
        embed.add_field(
            name="Uptime",
            value=format_seconds(time() - process.create_time()).split(".")[0],
        )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Utility(bot))
