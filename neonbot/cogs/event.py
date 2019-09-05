import sys

import discord
from addict import Dict
from discord.ext import commands

from .. import __title__, bot
from ..helpers import log
from ..helpers.constants import PERMISSION, TIMEZONE
from ..helpers.date import date_format
from ..helpers.utils import Embed
from .music import get_player
from .utility import chatbot

IGNORED_DELETEONCMD = ["eval", "evalmusic", "prune"]

commands_executed = 0


def get_activity():
    settings = bot.db.get_settings().settings
    activity_type = settings.game.type.lower()
    activity_name = settings.game.name
    status = settings.status

    return discord.Activity(
        name=activity_name,
        type=discord.ActivityType[activity_type],
        status=discord.Status[status],
    )


class Event(commands.Cog):
    @staticmethod
    @bot.event
    async def on_ready():
        await bot.change_presence(activity=get_activity())
        log.info(f"Logged in as {bot.user}")

    @staticmethod
    @bot.event
    async def on_disconnect():
        log.info(f"{__title__} disconnected")

    @staticmethod
    @bot.event
    async def on_message(message):
        def check_alias():
            nonlocal message
            config = bot.db.get_guild(message.guild.id).config
            arr = [x for x in config.aliases if x.name == message.content]
            if len(arr) > 0:
                message.content = arr[0].cmd.format(config.prefix)
                return True
            return False
        print(message.content)
        print(bot.user.mention)
        if message.content.startswith(bot.user.mention):
            msg = " ".join(message.content.split(" ")[1:])
            log.cmd(message, f"Process chatbot: {msg}")
            response = await chatbot(message.author.id, msg)
            await message.channel.send(
                embed=Embed(f"{message.author.mention} {response.conversation.say.bot}")
            )
        elif message.channel.type.name == "private":
            if message.content.lower() == "invite":
                application = await bot.application_info()
                await message.channel.send(
                    embed=Embed(
                        f"Bot invite link: https://discordapp.com/oauth2/authorize?client_id={application.id}&scope=bot&permissions={PERMISSION}"
                    )
                )
            elif (
                message.author.id not in bot.owner_ids
                and message.author.id != bot.user.id
            ):
                for owner in bot.owner_ids:
                    embed = Embed(
                        title=f"DM from {message.author}", description=message.content
                    )
                    await bot.get_user(owner).send(embed=embed)
        else:
            if check_alias():
                await message.channel.send(
                    embed=Embed(f"Alias found. Executing `{message.content}`."),
                    delete_after=5,
                )
            await bot.process_commands(message)

    @staticmethod
    @bot.event
    async def on_voice_state_update(member, before, after):
        if member.bot:
            return

        config = bot.db.get_guild(member.guild.id).config
        music = get_player(member.guild.id).connection

        if before.channel != after.channel:
            voice_tts = bot.get_channel(int(config.channel.voicetts or -1))
            log = bot.get_channel(int(config.channel.log or -1))
            members = lambda members: len(
                list(filter(lambda member: not member.bot, members))
            )

            if after.channel:
                msg = f"**{member.name}** has connected to **{after.channel.name}**"
                if music and music.is_paused() and members(after.channel.members) > 0:
                    music.resume()
            else:
                msg = f"**{member.name}** has disconnected to **{before.channel.name}**"
                if (
                    music
                    and music.is_playing()
                    and members(before.channel.members) == 0
                ):
                    music.pause()

            if voice_tts:
                await voice_tts.send(msg.replace("**", ""), tts=True, delete_after=3)
            if log:
                embed = Embed(f"`{date_format()}`:bust_in_silhouette:{msg}")
                embed.set_author(
                    name="Voice Presence Update", icon_url=bot.user.avatar_url
                )
                await log.send(embed=embed)

    @staticmethod
    @bot.event
    async def on_member_update(before, after):
        if before.bot:
            return

        config = bot.db.get_guild(before.guild.id).config
        log = bot.get_channel(int(config.channel.log or -1))
        msg = None

        if before.status != after.status:
            msg = f"**{before.name}** is now **{after.status}**."
        elif before.activities and not after.activities:
            activity = before.activities[-1]
            msg = f"**{before.name}** is done {activity.type.name} **{activity.name}**."
        elif not before.activities and after.activities:
            activity = after.activities[-1]
            msg = f"**{before.name}** is now {activity.type.name} **{activity.name}**."

        if log and msg:
            embed = Embed(f"`{date_format()}`:bust_in_silhouette:{msg}")
            embed.set_author(name="User Presence Update", icon_url=bot.user.avatar_url)
            await log.send(embed=embed)

    @staticmethod
    @bot.event
    async def on_member_join(member):
        config = bot.db.get_guild(member.guild.id).config
        channel = bot.get_channel(int(config.channel.log))

        msg = f"**{member.name}** joined the server."

        if channel:
            embed = Embed(f"`{date_format()}`:bust_in_silhouette:{msg}")
            embed.set_author(name="Member Join", icon_url=bot.user.avatar_url)
            channel.send()

    @staticmethod
    @bot.event
    async def on_member_remove(member):
        config = bot.db.get_guild(member.guild.id).config
        channel = bot.get_channel(int(config.channel.log))

        msg = f"**{member.name}** left the server."

        if channel:
            embed = Embed(f"`{date_format()}`:bust_in_silhouette:{msg}")
            embed.set_author(name="Member Leave", icon_url=bot.user.avatar_url)
            channel.send()

    @staticmethod
    @bot.event
    async def on_command(ctx):
        global commands_executed
        commands_executed += 1

        config = bot.db.get_guild(ctx.guild.id).config
        log.cmd(ctx, ctx.message.content)

        if ctx.command.name not in IGNORED_DELETEONCMD and config.deleteoncmd:
            await ctx.message.delete()

    @staticmethod
    @bot.event
    async def on_command_error(ctx, error):
        if hasattr(ctx.command, "on_error"):
            return

        error = getattr(error, "original", error)
        ignored = (commands.CheckFailure, discord.NotFound)

        if isinstance(error, ignored):
            return

        log.cmd(ctx, "Command error:", error)

        if isinstance(error, commands.CommandNotFound):
            return await ctx.send(embed=Embed(str(error)))

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(
                embed=Embed(f"{str(error).capitalize()} {ctx.command.usage or ''}")
            )

        raise error


def setup(bot):
    bot.add_cog(Event(bot))
