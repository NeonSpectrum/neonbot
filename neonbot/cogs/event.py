import logging
import traceback
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Union, cast

import nextcord
from nextcord.ext import commands
from nextcord.utils import escape_markdown

from .utility import chatbot
from .. import bot
from ..classes.embed import Embed
from ..helpers import exceptions
from ..helpers.constants import EXCLUDED_TYPING, IGNORED_DELETEONCMD
from ..helpers.date import date_format, format_seconds
from ..helpers.log import Log

log = cast(Log, logging.getLogger(__name__))


async def get_ctx(message: nextcord.Message) -> Tuple[bool, commands.Context]:
    aliases: List[dict] = []
    if message.guild:
        guild = bot.db.get_guild(message.guild.id)
        aliases = [x for x in guild.get('aliases') if x['name'] == message.content]
        if any(aliases):
            message.content = aliases[0]['cmd'].format(guild.get('prefix'))
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
        # log.warn("Disconnected!")
        pass

    @staticmethod
    @bot.event
    async def on_ready() -> None:
        await bot.db.process_database(bot.guilds)
        log.info("Ready!\n")
        await bot.send_restart_message()
        bot.set_ready()

    @staticmethod
    @bot.event
    async def on_resumed() -> None:
        presence = bot.get_presence()
        await bot.change_presence(status=presence[0], activity=presence[1])
        # log.info("Resumed!\n")

    @staticmethod
    @bot.event
    async def on_message(message: nextcord.Message) -> None:
        if not bot.is_ready() or message.author.id == bot.user.id:
            return

        is_alias, ctx = await get_ctx(message)

        if message.content.replace("<@!", "<@", 1).startswith(bot.user.mention):
            log.cmd(ctx, message.content)
            return await chatbot(message)
        elif str(ctx.channel.type) == "private":
            if message.content.lower() == "invite":
                return await bot.send_invite_link(message)

            log.info(f"DM from {ctx.author}: {message.content}")
            await bot.send_to_owner(
                embed=Embed(title=f"DM from {ctx.author}", description=message.content),
                sender=ctx.author.id,
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
    async def on_message_delete(message: nextcord.Message) -> None:
        if message.author.bot:
            return

        guild = bot.db.get_guild(message.guild.id)
        log_channel = bot.get_channel(int(guild.get('channel.msgdelete') or -1))

        if log_channel:
            content = []

            if message.content:
                content.append(message.content)

            if len(message.attachments) > 0:
                content += [attachment.proxy_url for attachment in message.attachments]

            embed = Embed(f"**{message.author}**\n" + '\n'.join(content))
            embed.set_author(name="Message Deletion", icon_url=bot.user.display_avatar)
            embed.set_footer(text=date_format())
            await log_channel.send(embed=embed)

    @staticmethod
    @bot.event
    async def on_voice_state_update(
        member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState
    ) -> None:
        if member.bot:
            return

        guild = bot.db.get_guild(member.guild.id)
        player = bot.music.get(member.guild.id)
        voice_channel = after.channel or before.channel

        if player and player.last_voice_channel:
            voice_members = [
                member
                for member in player.last_voice_channel.members
                if not member.bot
            ]

            if any(voice_members):
                await player.on_member_join()
            else:
                await player.on_member_leave()

        if before.channel != after.channel:
            voice_tts_channel = bot.get_channel(int(guild.get('channel.voicetts') or -1))
            log_channel = bot.get_channel(int(guild.get('channel.voice_log') or -1))

            role = voice_channel.guild.default_role
            permission = voice_channel.permissions_for(role)
            readable = all([permission.view_channel, permission.connect])

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
                    name="Voice Presence Update", icon_url=bot.user.display_avatar
                )
                embed.set_footer(text=date_format())
                await log_channel.send(embed=embed)

    @staticmethod
    @bot.event
    async def on_presence_update(before: nextcord.Member, after: nextcord.Member) -> None:
        if before.bot:
            return

        guild = bot.db.get_guild(before.guild.id)
        log_channel = bot.get_channel(int(guild.get('channel.presence_log') or -1))

        embed = Embed()
        embed.set_footer(text=date_format())

        if before.status != after.status:
            embed.set_author(name="User Presence Update", icon_url=bot.user.display_avatar)
            msg = f"**{before.name}** is now **{after.status}**."
            embed.description = f":bust_in_silhouette:{msg}"
        elif before.activities != after.activities:
            last = before.activities and before.activities[-1]
            current = after.activities and after.activities[-1]

            def get_image(
                activity: Union[nextcord.Spotify, nextcord.Game, nextcord.Activity]
            ) -> Optional[str]:
                if isinstance(activity, nextcord.Spotify):
                    return activity.album_cover_url
                elif isinstance(activity, nextcord.Activity):
                    return activity.large_image_url or activity.small_image_url
                return None

            embed.description = f":bust_in_silhouette:**{before.name}** is"
            embed.set_author(
                name="Activity Presence Update", icon_url=bot.user.display_avatar
            )

            if isinstance(current, nextcord.Spotify):
                if getattr(last, "title", None) == current.title:
                    return

                embed.set_thumbnail(get_image(current))
                embed.add_field("Title", current.title)
                embed.add_field("Artist", current.artist)
            elif isinstance(current, (nextcord.Activity, nextcord.Game)):
                if getattr(last, "name", None) == current.name:
                    return

                embed.set_thumbnail(get_image(current))
                if getattr(current, "details", None):
                    embed.add_field("Details", escape_markdown(current.details))

            if not current:
                embed.set_thumbnail(get_image(last))
                embed.description += f" done {last.type.name} **{last.name}**."
                if hasattr(last, 'start') and last.start:
                    embed.add_field(
                        name="Time Elapsed",
                        value=format_seconds(
                            datetime.now(tz=timezone.utc).timestamp() - last.start.timestamp()
                        ),
                    )
            else:
                embed.description += f" now {current.type.name} **{current.name}**."

        if log_channel and embed.description:
            await log_channel.send(embed=embed)

    @staticmethod
    @bot.event
    async def on_member_join(member: nextcord.Member) -> None:
        guild = bot.db.get_guild(member.guild.id)
        channel = bot.get_channel(int(guild.get('channel.presence_log') or -1))

        msg = f"**{member.name}** joined the server."

        if channel:
            embed = Embed(f":bust_in_silhouette:{msg}")
            embed.set_author(name="Member Join", icon_url=bot.user.display_avatar)
            embed.set_footer(text=date_format())
            await channel.send(embed=embed)

    @staticmethod
    @bot.event
    async def on_member_remove(member: nextcord.Member) -> None:
        guild = bot.db.get_guild(member.guild.id)
        channel = bot.get_channel(int(guild.get('channel.presence_log') or -1))

        msg = f"**{member.name}** left the server."

        if channel:
            embed = Embed(f":bust_in_silhouette:{msg}")
            embed.set_author(name="Member Leave", icon_url=bot.user.display_avatar)
            embed.set_footer(text=date_format())
            await channel.send(embed=embed)

    @staticmethod
    @bot.event
    async def on_guild_join(guild: nextcord.Guild) -> None:
        await bot.db.process_database([guild])
        log.info(f"Bot joined {guild.name}")

    @staticmethod
    @bot.event
    async def on_command(ctx: commands.Context) -> None:
        bot.commands_executed.append(ctx.message.content)

        log.cmd(ctx, ctx.message.content, guild=ctx.guild or "N/A")

        if str(ctx.channel.type) == "private":
            return

        guild = bot.db.get_guild(ctx.guild.id)

        if ctx.command.name not in IGNORED_DELETEONCMD and guild.get('deleteoncmd'):
            await bot.delete_message(ctx.message)

    @staticmethod
    @bot.event
    async def on_command_error(ctx: commands.Context, error: Exception) -> None:
        if hasattr(ctx.command, "on_error"):
            return

        error = getattr(error, "original", error)
        ignored = nextcord.NotFound, commands.BadArgument, commands.CheckFailure
        send_msg = commands.CommandNotFound, exceptions.YtdlError, commands.MissingPermissions

        tb = traceback.format_exception(
            etype=type(error), value=error, tb=error.__traceback__
        )

        tb_msg = "\n".join(tb)[:1000] + "..."

        if type(error) in ignored:
            return

        log.cmd(ctx, f"Command error: {error}")

        if isinstance(error, send_msg):
            await ctx.send(embed=Embed(error))
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                embed=Embed(f"{str(error).capitalize()} {ctx.command.usage or ''}")
            )
            return

        await ctx.send(
            embed=Embed(
                "There was an error executing the command. Please check the logs."
            ),
            delete_after=60
        )

        embed = Embed(
            title="Traceback Exception",
            description=f"Command: ```{ctx.message.content}``````py\n{tb_msg}```",
        )

        await bot.send_to_owner(embed=embed)

        raise error


# noinspection PyShadowingNames
def setup(bot: commands.Bot) -> None:
    bot.add_cog(Event())
