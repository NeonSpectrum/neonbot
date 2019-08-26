import random

import requests
from addict import Dict
from discord.ext import commands

from bot import bot
from helpers.utils import Embed

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


def setup(bot):
  bot.add_cog(Utility(bot))
