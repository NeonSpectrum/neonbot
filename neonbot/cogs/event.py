import logging
import traceback
from typing import List, Tuple, cast

import discord
from addict import Dict
from discord.ext import commands

from .. import bot
from ..helpers import exceptions
from ..helpers.constants import EXCLUDED_TYPING, IGNORED_DELETEONCMD
from ..helpers.date import date_format
from ..helpers.log import Log
from ..helpers.utils import Embed
from .utility import chatbot

log = cast(Log, logging.getLogger(__name__))


async def get_ctx(message: discord.Message) -> Tuple[bool, commands.Context]:
    aliases: List[Dict] = []
    if message.guild:
        config = bot.db.get_guild(message.guild.id).config
        aliases = [x for x in config.aliases if x.name == message.content]
        if any(aliases):
            message.content = aliases[0].cmd.format(config.prefix)
    return any(aliases), await bot.get_context(message)


class Event(commands.Cog):
    @staticmethod
    @bot.event
    async def on_connect() -> None:
        await bot.fetch_app_info()
        log.info(f"Logged in as {bot.user}")

    @staticmethod
    @bot.event
    async def on_disconnect() -> None:
        log.warn("Disconnected!")

    @staticmethod
    @bot.event
    async def on_ready() -> None:
        log.info("Ready!\n")
        await bot.send_restart_message()

    @staticmethod
    @bot.event
    async def on_message(message: discord.Message) -> None:
        if message.author.id == bot.user.id:
            return

        is_alias, ctx = await get_ctx(message)

        if message.content.replace("<@!", "<@", 1).startswith(bot.user.mention):
            log.cmd(ctx, message.content)
            return await chatbot(message)
        elif ctx.channel.type.name == "private":
            if message.content.lower() == "invite":
                return await bot.send_invite_link(message.channel)

            log.info(f"DM from {ctx.author}: {message.content}")
            await bot.send_to_all_owners(
                embed=Embed(title=f"DM from {ctx.author}", description=message.content),
                excluded=[ctx.author.id],
            )
            if not ctx.command:
                await chatbot(message, dm=True)

        if is_alias:
            msg = f"Alias found. Executing `{ctx.message.content}`."
            log.cmd(ctx, msg)
            await ctx.send(embed=Embed(msg), delete_after=5)
        if ctx.command is not None:
            if ctx.command.name not in EXCLUDED_TYPING:
                await ctx.channel.trigger_typing()
            await bot.process_commands(message)

    @staticmethod
    @bot.event
    async def on_voice_state_update(
        member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if member.bot:
            return

        config = bot.db.get_guild(member.guild.id).config
        player = bot.music[member.guild.id]
        voice_channel = after.channel or before.channel

        if player and player.connection:
            voice_members = [
                member
                for member in voice_channel.members
                if not member.bot and not member.voice.self_deaf
            ]
            if player.connection.is_playing() and not voice_members:
                msg = "Player will reset after 10 minutes."
                log.cmd(member, msg, channel=voice_channel, user="N/A")
                player.messages.auto_paused = await player.ctx.send(embed=Embed(msg))
                player.connection.pause()
                player.reset_timeout.start()
            elif player.connection.is_paused() and any(voice_members):
                if player.messages.auto_paused:
                    await player.messages.auto_paused.delete()
                    player.messages.auto_paused = None
                player.connection.resume()
                player.reset_timeout.cancel()

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
                embed = Embed(f":bust_in_silhouette:{msg}")
                embed.set_author(
                    name="Voice Presence Update", icon_url=bot.user.avatar_url
                )
                embed.set_footer(text=date_format())
                await log_channel.send(embed=embed)

    @staticmethod
    @bot.event
    async def on_member_update(before: discord.Member, after: discord.Member) -> None:
        if before.bot:
            return

        config = bot.db.get_guild(before.guild.id).config
        log_channel = bot.get_channel(int(config.channel.log or -1))

        msg = None

        embed = Embed()
        embed.set_footer(text=date_format())

        if before.status != after.status:
            embed.set_author(name="User Presence Update", icon_url=bot.user.avatar_url)
            msg = f"**{before.name}** is now **{after.status}**."
            embed.description = f":bust_in_silhouette:{msg}"
        elif before.activities != after.activities:
            last = before.activities and before.activities[-1]
            current = after.activities and after.activities[-1]

            if isinstance(current, discord.Game) and getattr(last, "title") == getattr(current, "title":
                return

            embed.description = f":bust_in_silhouette:**{before.name}** is"
            embed.set_author(
                name="Activity Presence Update", icon_url=bot.user.avatar_url
            )

            if current and isinstance(current, discord.Spotify):
                embed.set_thumbnail(url=current.album_cover_url)
                embed.add_field(name="Title", value=current.title, inline=False)
                embed.add_field(name="Artist", value=current.artist, inline=False)
            elif isinstance(current, (discord.Activity, discord.Game)):
                image = getattr(current, "small_image_url") or getattr(current, "large_image_url")
                if image:
                    embed.set_thumbnail(url=image)
                if current.details:
                    embed.add_field(
                        name="Details",
                        value=discord.utils.escape_markdown(current.details),
                        inline=False,
                    )

            if not current:
                embed.description += f" done {last.type.name} **{last.name}**."
                embed.clear_fields()
                embed._thumbnail = {}
            else:
                embed.description += f" now {current.type.name} **{current.name}**."

        if log_channel and embed.description:
            await log_channel.send(embed=embed)

    @staticmethod
    @bot.event
    async def on_member_join(member: discord.Member) -> None:
        config = bot.db.get_guild(member.guild.id).config
        channel = bot.get_channel(int(config.channel.log))

        msg = f"**{member.name}** joined the server."

        if channel:
            embed = Embed(f":bust_in_silhouette:{msg}")
            embed.set_author(name="Member Join", icon_url=bot.user.avatar_url)
            embed.set_footer(text=date_format())
            channel.send()

    @staticmethod
    @bot.event
    async def on_member_remove(member: discord.Member) -> None:
        config = bot.db.get_guild(member.guild.id).config
        channel = bot.get_channel(int(config.channel.log))

        msg = f"**{member.name}** left the server."

        if channel:
            embed = Embed(f":bust_in_silhouette:{msg}")
            embed.set_author(name="Member Leave", icon_url=bot.user.avatar_url)
            embed.set_footer(text=date_format())
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
        ignored = commands.CheckFailure, discord.NotFound
        send_msg = commands.CommandNotFound, exceptions.YtdlError

        tb = traceback.format_exception(
            etype=type(error), value=error, tb=error.__traceback__
        )

        tb_msg = "\n".join(tb)

        if isinstance(error, ignored):
            return

        log.cmd(ctx, f"Command error: {error}")

        if isinstance(error, send_msg):
            return await ctx.send(embed=Embed(error))

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(
                embed=Embed(f"{str(error).capitalize()} {ctx.command.usage or ''}")
            )

        await ctx.send(
            embed=Embed(
                f"There was an error executing the command. Please check the logs."
            )
        )

        embed = Embed(
            title="Traceback Exception",
            description=f"Command: ```{ctx.message.content}```\n```py\n{tb_msg}```",
        )

        await bot.send_to_all_owners(embed=embed)

        raise error


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Event())
