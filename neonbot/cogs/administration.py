import asyncio
import inspect

import discord
from discord.ext import commands

from bot import env, owner_ids
from helpers.database import Database
from helpers.utils import Embed, check_args


class Administration(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command(hidden=True)
  @commands.is_owner()
  async def eval(self, ctx, *, args):
    bot = self.bot
    env = {'bot': bot, 'discord': discord, 'commands': commands, 'ctx': ctx, '__import__': __import__}

    def cleanup(code):
      if code.startswith('```') and code.endswith('```'):
        return '\n'.join(code.splitlines()[1:-1])
      return code

    try:
      code = cleanup(args)
      lines = [f"  {i}" for i in code.splitlines()]
      if len(lines) == 1:
        cmd = eval(code)
        output = (await cmd) if inspect.isawaitable(cmd) else cmd
      else:
        lines = '\n'.join(lines)
        exec(f"async def x():\n{lines}\n", env)
        output = await eval("x()", env)
      await ctx.message.add_reaction('👌')
    except Exception as e:
      output = str(e)
      await ctx.message.add_reaction('❌')
    if output and isinstance(output, str):
      await ctx.send(f"```py\n{output}```")

  @commands.command(hidden=True)
  @commands.is_owner()
  async def generatelog(self, ctx):
    with open("./debug.log", "r") as f:
      text = f.read()
    res = await self.bot.session.post("https://pastebin.com/api/api_post.php",
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
  async def setstatus(self, ctx, arg):
    if not await check_args(ctx, arg, ["online", "offline", "dnd", "idle"]): return

    database = Database()
    settings = database.settings
    settings.status = arg
    settings = database.update_settings().settings

    await self.bot.change_presence(status=discord.Status[arg])
    await ctx.send(embed=Embed(description=f"Status is now set to {settings.prefix}."))

  @commands.command()
  @commands.is_owner()
  async def setpresence(self, ctx, presence_type, *, name):
    if not await check_args(ctx, presence_type, ["watching", "listening", "playing"]): return

    database = Database()
    settings = database.settings
    settings.game.type = presence_type
    settings.game.name = name
    settings = database.update_settings().settings

    await self.bot.change_presence(
      activity=discord.Activity(name=name, type=discord.ActivityType[settings.game.type]))
    await ctx.send(embed=Embed(
      description=f"Presence is now set to {settings.game.type} {settings.game.name}."))

  @commands.command()
  async def alias(self, ctx, name, *, cmd):
    database = Database(ctx.guild.id)
    aliases = database.config.aliases
    ids = [i for i, x in enumerate(aliases) if x.name == name]
    if len(ids) > 0:
      if int(aliases[ids[0]].owner) != ctx.author.id and ctx.author.id not in owner_ids:
        return await ctx.send(embed=Embed(description=f"You are not the owner of the alias."), delete_after=5)
      aliases[ids[0]].cmd = cmd.replace(ctx.prefix, "{0}", 1) if cmd.startswith(ctx.prefix) else cmd
    else:
      database.config.aliases.append({"name": name, "cmd": cmd, "owner": ctx.author.id})
    database.update_config()
    await ctx.send(embed=Embed(description=f"Message with exactly `{name}` will now execute `{cmd}`"),
                   delete_after=10)

  @commands.command()
  @commands.is_owner()
  async def deletealias(self, ctx, name):
    database = Database(ctx.guild.id)
    aliases = database.config.aliases
    ids = [i for i, x in enumerate(aliases) if x.name == name]
    if len(ids) == 0:
      return await ctx.send(embed=Embed(description=f"Alias doesn't exists."), delete_after=5)
    if int(aliases[ids[0]].owner) != ctx.author.id and ctx.author.id not in owner_ids:
      return await ctx.send(embed=Embed(description=f"You are not the owner of the alias."), delete_after=5)
    del aliases[ids[0]]
    database.update_config()
    await ctx.send(embed=Embed(description=f"Alias`{name}` has been deleted."), delete_after=5)

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
  bot.add_cog(Administration(bot))
