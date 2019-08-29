import asyncio

import discord
from aiohttp import ClientSession
from discord.ext import commands

from bot import env
from helpers.database import Database
from helpers.utils import Embed


class Administrator(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command(hidden=True)
  @commands.is_owner()
  async def eval(self, ctx, *args):
    bot = self.bot
    try:
      if args[0] == "await":
        output = await eval(args[1])
      else:
        output = eval(args[0])
    except Exception as e:
      output = str(e)
    await ctx.send(f"```py\n{output}```")

  @commands.command(hidden=True)
  @commands.is_owner()
  async def generatelog(self, ctx):
    session = ClientSession()
    file = open("./debug.log", "r")
    text = file.read()
    file.close()
    res = await session.post("https://pastebin.com/api/api_post.php",
                             data={
                               "api_dev_key": env("PASTEBIN_API"),
                               "api_paste_code": text,
                               "api_option": "paste",
                               "api_paste_private": 1,
                               "paste_expire_date": "10M"
                             })
    paste_link = await res.text()
    paste_id = paste_link.split("/")[-1]
    await ctx.send(embed=Embed(description=f"Generated pastebin: https://pastebin.com/raw/{paste_id}"))
    await session.close()

  @commands.command(hidden=True)
  @commands.is_owner()
  async def reload(self, ctx, *, args):
    try:
      self.bot.reload_extension("modules." + args)
    except Exception as e:
      await ctx.send(embed=Embed(description=str(e)))
    else:
      await ctx.send(embed=Embed(description=f"Reloaded module: `{args}`."))

  @commands.command()
  @commands.guild_only()
  @commands.has_permissions(manage_messages=True)
  async def prune(self, ctx, count: int = 1, member: discord.Member = None):
    config = Database(ctx.guild.id).config

    if config.deleteoncmd:
      count += 1

    limit = 100 if member else count

    def check(message):
      nonlocal count

      if count <= 0:
        return False

      count -= 1
      return not member or message.author.id == member.id

    await ctx.channel.purge(limit=limit, check=check)

  @commands.command()
  @commands.is_owner()
  async def prefix(self, ctx, arg):
    database = Database(ctx.guild.id)
    config = database.config
    config.prefix = arg
    config = database.update_config().config
    await ctx.send(embed=Embed(description=f"Prefix is now set to {config.prefix}."))

  @commands.command()
  @commands.is_owner()
  async def deleteoncmd(self, ctx):
    database = Database(ctx.guild.id)
    config = database.config
    config.deleteoncmd = not config.deleteoncmd
    config = database.update_config().config
    await ctx.send(embed=Embed(
      description=f"Delete on command is now set to {'enabled' if config.deleteoncmd else 'disabled'}."))

  @commands.command()
  @commands.is_owner()
  async def voicetts(self, ctx):
    database = Database(ctx.guild.id)
    config = database.config

    if config.channel.voicetts != ctx.channel.id:
      config.channel.voicetts = ctx.channel.id
    else:
      config.channel.voicetts = None

    config = database.update_config().config

    if config.channel.voicetts:
      await ctx.send(embed=Embed(description=f"Voice TTS is now set to this channel."))
    else:
      await ctx.send(embed=Embed(description=f"Voice TTS is now disabled."))

  @commands.command()
  @commands.is_owner()
  async def logger(self, ctx):
    database = Database(ctx.guild.id)
    config = database.config

    if config.channel.log != ctx.channel.id:
      config.channel.log = ctx.channel.id
    else:
      config.channel.log = None

    config = database.update_config().config

    if config.channel.log:
      await ctx.send(embed=Embed(description=f"Logger is now set to this channel."))
    else:
      await ctx.send(embed=Embed(description=f"Logger is now disabled."))


def setup(bot):
  bot.add_cog(Administrator(bot))
