import logging
from typing import cast

import discord
from discord.ext import commands
from discord.utils import oauth_url

from .. import bot
from ..helpers.constants import PERMISSIONS
from ..helpers.date import date_format
from ..helpers.exceptions import YtdlError
from ..helpers.log import Log
from ..helpers.utils import Embed, send_to_all_owners
from .music import get_player
from .utility import chatbot

log = cast(Log, logging.getLogger(__name__))

IGNORED_DELETEONCMD = ["eval", "prune"]


class Event(commands.Cog):
    @staticmethod
    @bot.event
    async def on_connect() -> None:
        if not bot.app_info:
            await bot.set_app_info()
        log.info(f"Logged in as {bot.user}")

    @staticmethod
    @bot.event
    async def on_disconnect() -> None:
        log.warn("Disconnected!")

    @staticmethod
    @bot.event
    async def on_ready() -> None:
        log.info("Ready!")
        await bot.send_restart_message()

    @staticmethod
    @bot.event
    async def on_message(message: discord.Message) -> None:
        def check_alias() -> bool:
            nonlocal message
            config = bot.db.get_guild(message.guild.id).config
            arr = [x for x in config.aliases if x.name == message.content]
            if len(arr) > 0:
                message.content = arr[0].cmd.format(config.prefix)
                return True
            return False

        if message.content.replace("<@!", "<@", 1).startswith(bot.user.mention):
            log.cmd(message, message.content)
            async with message.channel.typing():
                await chatbot(message)
            return
        elif message.channel.type.name == "private":
            if message.content.lower() == "invite":
                url = oauth_url(
                    bot.app_info.id, discord.Permissions(permissions=PERMISSIONS)
                )
                await message.channel.send(f"Bot invite link: {url}")
                return log.info(f"Sent an invite link to: {message.author}")
            elif message.author.id != bot.user.id:
                log.info(f"DM from {message.author}: {message.content}")
                await send_to_all_owners(
                    embed=Embed(
                        title=f"DM from {message.author}", description=message.content
                    ),
                    excluded=[message.author.id],
                )
                if not message.content.startswith(bot.default_prefix):
                    async with message.channel.typing():
                        await chatbot(message, dm=True)
                    return
        elif check_alias():
            msg = f"Alias found. Executing `{message.content}`."
            log.cmd(message, msg)
            await message.channel.send(embed=Embed(msg), delete_after=5)
        await bot.process_commands(message)

    @staticmethod
    @bot.event
    async def on_voice_state_update(
        member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if member.bot:
            return

        config = bot.db.get_guild(member.guild.id).config
        player = get_player(member.guild)
        voice_channel = after.channel or before.channel

        if player and player.connection:
            voice_members = [
                member
                for member in voice_channel.members
                if not member.bot and not member.voice.self_deaf
            ]
            if player.connection.is_playing() and len(voice_members) == 0:
                msg = "Player paused because no users are listening."
                log.cmd(member, msg, channel=voice_channel, user="N/A")
                player.messages.auto_paused = await player.channel.send(
                    embed=Embed(msg)
                )
                player.connection.pause()
            elif player.connection.is_paused() and len(voice_members) > 0:
                if player.messages.auto_paused:
                    await player.messages.auto_paused.delete()
                    player.messages.auto_paused = None
                log.cmd(
                    member,
                    "Player resumed because someone will be listening.",
                    channel=voice_channel,
                    user="N/A",
                )
                player.connection.resume()

        if before.channel != after.channel:
            voice_tts_channel = bot.get_channel(int(config.channel.voicetts or -1))
            log_channel = bot.get_channel(int(config.channel.log or -1))

            role = voice_channel.guild.default_role
            readable = voice_channel.overwrites_for(role).read_messages is not False

            if after.channel:
                msg = f"**{member.name}** has connected to **{voice_channel.name}**"
            else:
                msg = f"**{member.name}** has disconnected to **{voice_channel.name}**"

            if voice_tts_channel:
                await voice_tts_channel.send(
                    msg.replace("**", ""), tts=True, delete_after=0
                )
            if log_channel and readable:
                embed = Embed(f"`{date_format()}`:bust_in_silhouette:{msg}")
                embed.set_author(
                    name="Voice Presence Update", icon_url=bot.user.avatar_url
                )
                await log_channel.send(embed=embed)

    @staticmethod
    @bot.event
    async def on_member_update(before: discord.Member, after: discord.Member) -> None:
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
    async def on_member_join(member: discord.Member) -> None:
        config = bot.db.get_guild(member.guild.id).config
        channel = bot.get_channel(int(config.channel.log))

        msg = f"**{member.name}** joined the server."

        if channel:
            embed = Embed(f"`{date_format()}`:bust_in_silhouette:{msg}")
            embed.set_author(name="Member Join", icon_url=bot.user.avatar_url)
            channel.send()

    @staticmethod
    @bot.event
    async def on_member_remove(member: discord.Member) -> None:
        config = bot.db.get_guild(member.guild.id).config
        channel = bot.get_channel(int(config.channel.log))

        msg = f"**{member.name}** left the server."

        if channel:
            embed = Embed(f"`{date_format()}`:bust_in_silhouette:{msg}")
            embed.set_author(name="Member Leave", icon_url=bot.user.avatar_url)
            channel.send()

    @staticmethod
    @bot.event
    async def on_command(ctx: commands.Context) -> None:
        bot.commands_executed.append(ctx.message.content)

        if ctx.channel.type.name == "private":
            return

        config = bot.db.get_guild(ctx.guild.id).config
        log.cmd(ctx, ctx.message.content)

        if ctx.command.name not in IGNORED_DELETEONCMD and config.deleteoncmd:
            await ctx.message.delete()

    @staticmethod
    @bot.event
    async def on_command_error(ctx: commands.Context, error: Exception) -> None:
        if hasattr(ctx.command, "on_error"):
            return

        error = getattr(error, "original", error)
        ignored = (commands.CheckFailure, discord.NotFound)
        send_msg = (commands.CommandNotFound, YtdlError)

        if isinstance(error, ignored):
            return

        log.cmd(ctx, f"Command error: {error}")

        if isinstance(error, send_msg):
            return await ctx.send(embed=Embed(str(error)))

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(
                embed=Embed(f"{str(error).capitalize()} {ctx.command.usage or ''}")
            )

        await send_to_all_owners(
            embed=Embed(title=error.__class__.__name__, description=str(error))
        )

        raise error


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Event())
