import logging

import arrow
import discord
from addict import Dict
from discord.ext import commands

from bot import bot
from helpers import log
from helpers.constants import TIMEZONE
from helpers.database import Database
from helpers.utils import Embed

from .utility import chatbot


def get_activity():
  settings = Database().settings
  activity_type = settings.game.type.lower()
  activity_name = settings.game.name
  status = settings.status

  return discord.Activity(name=activity_name,
                          type=discord.ActivityType[activity_type],
                          status=discord.Status[status])


class Event(commands.Cog):
  @bot.event
  async def on_ready():
    bot.help_command.verify_check = False
    await bot.change_presence(activity=get_activity())
    log.info(f"Logged in as {bot.user}")

  @bot.event
  async def on_message(message):
    if message.content.startswith(bot.user.mention):
      msg = " ".join(message.content.split(" ")[1:])
      response = chatbot(message.author.id, msg).conversation.say.bot
      await message.channel.send(embed=Embed(description=f"{message.author.mention} {response}"))
    else:
      await bot.process_commands(message)

  @bot.event
  async def on_voice_state_update(member, before, after):
    if member.bot: return

    config = Database(member.guild.id).config
    if before.channel != after.channel:
      voice_tts = bot.get_channel(int(config.channel.voicetts or -1))
      log = bot.get_channel(int(config.channel.log or -1))

      if after.channel:
        msg = f"**{member.name}** has connected to **{after.channel.name}**"
      else:
        msg = f"**{member.name}** has disconnected to **{before.channel.name}**"

      if voice_tts:
        await voice_tts.send(msg.replace("**", ""), tts=True, delete_after=3)
      if log:
        embed = Embed(
          description=f"`{arrow.now('Asia/Manila').format('YYYY-MM-DD hh:mm:ss A')}`:bust_in_silhouette:{msg}"
        )
        embed.set_author(name="Voice Presence Update", icon_url=bot.user.avatar_url)
        await log.send(embed=embed)

  @bot.event
  async def on_member_update(before, after):
    if before.bot: return

    config = Database(before.guild.id).config
    log = bot.get_channel(int(config.channel.log or -1))
    msg = None

    def get_activity_status(activity):
      if isinstance(activity, discord.Game):
        return f"playing **{activity.name}**"
      elif isinstance(activity, discord.Activity):
        return f"{activity.type.name} **{activity.name}**"
      elif isinstance(activity, discord.Spotify):
        return f"listening **{activity.title}**"

    if before.status != after.status:
      msg = f"**{before.name}** is now **{after.status}**."
    elif before.activities and not after.activities:
      activity = before.activities[-1]
      msg = f"**{before.name}** is done {get_activity_status(activity)}."
    elif not before.activities and after.activities:
      activity = after.activities[-1]
      msg = f"**{before.name}** is now {get_activity_status(activity)}."

    if log and msg:
      embed = Embed(
        description=f"`{arrow.now('Asia/Manila').format('YYYY-MM-DD hh:mm:ss A')}`:bust_in_silhouette:{msg}")
      embed.set_author(name="User Presence Update", icon_url=bot.user.avatar_url)
      await log.send(embed=embed)

  @bot.event
  async def on_member_join(member):
    config = Database(member.guild.id).config
    channel = bot.get_channel(int(config.channel.log))

    msg = f"**{member.user}** joined the server."

    if channel:
      embed = Embed(
        description=f"`{arrow.now('Asia/Manila').format('YYYY-MM-DD hh:mm:ss A')}`:bust_in_silhouette:{msg}")
      embed.set_author(name="Member Join", icon_url=bot.user.avatar_url)
      channel.send()

  @bot.event
  async def on_member_remove(member):
    config = Database(member.guild.id).config
    channel = bot.get_channel(int(config.channel.log))

    msg = f"**{member.user}** left the server."

    if channel:
      embed = Embed(
        description=f"`{arrow.now('Asia/Manila').format('YYYY-MM-DD hh:mm:ss A')}`:bust_in_silhouette:{msg}")
      embed.set_author(name="Member Leave", icon_url=bot.user.avatar_url)
      channel.send()

  @bot.event
  async def on_command(ctx):
    config = Database(ctx.guild.id).config
    log.cmd(ctx, ctx.message.content)

    if ctx.command.name != "prune" and config.deleteoncmd:
      await ctx.message.delete()

  @bot.event
  async def on_command_error(ctx, error):
    ignored = (commands.CheckFailure, commands.MissingRequiredArgument)
    if isinstance(error, ignored):
      return

    log.cmd(ctx, "Command error:", error)

    if isinstance(error, commands.CommandNotFound):
      return await ctx.send(embed=Embed(description=str(error)))

    raise error


def setup(bot):
  bot.add_cog(Event(bot))
