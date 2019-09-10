import logging

import discord
from discord.ext import commands

from .. import bot
from ..helpers.constants import PERMISSION
from ..helpers.date import date_format
from ..helpers.utils import Embed
from .music import get_player
from .utility import chatbot

log = logging.getLogger(__name__)

IGNORED_DELETEONCMD = ["eval", "prune"]


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
    async def on_connect():
        await bot.change_presence(activity=get_activity())
        log.info(f"Logged in as {bot.user}")

    @staticmethod
    @bot.event
    async def on_disconnect():
        log.warn("Disconnected!")

    @staticmethod
    @bot.event
    async def on_ready():
        log.info("Connected!")

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

        if message.content.replace("<@!", "<@", 1).startswith(bot.user.mention):
            log.cmd(message, message.content)
            return await chatbot(message)
        elif message.channel.type.name == "private":
            if message.content.lower() == "invite":
                application = await bot.application_info()
                await message.channel.send(
                    embed=Embed(
                        f"Bot invite link: https://discordapp.com/oauth2/authorize?client_id={application.id}&scope=bot&permissions={PERMISSION}"
                    )
                )
                return log.info(f"Sent an invite link to: {message.author}")
            elif message.author.id != bot.user.id:
                log.info(f"DM from {message.author}: {message.content}")

                for owner in filter(lambda x: x != message.author.id, bot.owner_ids):
                    embed = Embed(
                        title=f"DM from {message.author}", description=message.content
                    )
                    await bot.get_user(owner).send(embed=embed)
        elif check_alias():
            msg = f"Alias found. Executing `{message.content}`."
            log.cmd(message, msg)
            await message.channel.send(embed=Embed(msg), delete_after=5)
        await bot.process_commands(message)

    @staticmethod
    @bot.event
    async def on_voice_state_update(member, before, after):
        if member.bot:
            return

        config = bot.db.get_guild(member.guild.id).config
        music = get_player(member.guild).connection

        if before.channel != after.channel:
            voice_tts_channel = bot.get_channel(int(config.channel.voicetts or -1))
            log_channel = bot.get_channel(int(config.channel.log or -1))
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

            if voice_tts_channel:
                await voice_tts_channel.send(
                    msg.replace("**", ""), tts=True, delete_after=0
                )
            if log_channel:
                embed = Embed(f"`{date_format()}`:bust_in_silhouette:{msg}")
                embed.set_author(
                    name="Voice Presence Update", icon_url=bot.user.avatar_url
                )
                await log_channel.send(embed=embed)

    @staticmethod
    @bot.event
    async def on_member_update(before, after):
        if before.bot:
            return

        config = bot.db.get_guild(before.guild.id).config
        log_channel = bot.get_channel(int(config.channel.log or -1))
        msg = None

        if before.status != after.status:
            msg = f"**{before.name}** is now **{after.status}**."
        elif before.activities and not after.activities:
            activity = before.activities[-1]
            msg = f"**{before.name}** is done {activity.type.name} **{activity.name}**."
        elif not before.activities and after.activities:
            activity = after.activities[-1]
            msg = f"**{before.name}** is now {activity.type.name} **{activity.name}**."

        if log_channel and msg:
            embed = Embed(f"`{date_format()}`:bust_in_silhouette:{msg}")
            embed.set_author(name="User Presence Update", icon_url=bot.user.avatar_url)
            await log_channel.send(embed=embed)

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
        bot.commands_executed += 1

        if ctx.channel.type.name == "private":
            return

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

        log.cmd(ctx, f"Command error: {error}")

        if isinstance(error, commands.CommandNotFound):
            return await ctx.send(embed=Embed(str(error)))

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(
                embed=Embed(f"{str(error).capitalize()} {ctx.command.usage or ''}")
            )

        raise error


def setup(bot):
    bot.add_cog(Event(bot))
