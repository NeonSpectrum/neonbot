import os
import random
from time import time

import psutil
import requests
from addict import Dict
from discord.ext import commands

from bot import bot, uptime
from helpers.utils import Embed, format_seconds

chatbot_users = Dict()


def chatbot(user_id, message):
  user = chatbot_users[user_id]
  if not user:
    user.requests = requests.Session()
  res = user.requests.get("https://program-o.com/v3/chat.php", params={"say": message})
  return Dict(res.json())


class Utility(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command()
  async def random(self, ctx, *args):
    await ctx.send(embed=Embed(description=random.choice(args)))

  @commands.command(aliases=["stats"])
  async def status(self, ctx):
    from .event import get_commands_executed

    process = psutil.Process(os.getpid())

    embed = Embed()
    embed.set_author(name="NeonBot v1.0.0", icon_url=bot.user.avatar_url)
    embed.add_field(name="Username", value=bot.user.name, inline=True)
    embed.add_field(name="Created On", value=f"{bot.user.created_at:%Y-%m-%d %I:%M:%S %p}", inline=True)
    embed.add_field(name="Created By", value="NeonSpectrum", inline=True)
    embed.add_field(name="Guilds", value=len(bot.guilds), inline=True)
    embed.add_field(name="Channels", value=sum(1 for _ in bot.get_all_channels()), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Commands Executed", value=get_commands_executed(), inline=True)
    embed.add_field(name="Ram Usage",
                    value=f"Approximately {(process.memory_info().rss / 1024000):.2f} MB",
                    inline=True)
    embed.add_field(name="Uptime", value=format_seconds(time() - uptime).split(".")[0], inline=True)

    await ctx.send(embed=embed)


def setup(bot):
  bot.add_cog(Utility(bot))
