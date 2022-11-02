import traceback
from datetime import datetime, timezone
from typing import Union, Optional

import discord
from discord.app_commands import AppCommandError
from discord.ext import commands
from discord.utils import escape_markdown

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.classes.player import Player
from neonbot.models.guild import Guild
from neonbot.utils import log, exceptions
from neonbot.utils.functions import format_seconds
from neonbot.utils.functions import get_command_string


class Event(commands.Cog):
    @staticmethod
    @bot.event
    async def on_connect() -> None:
        await bot.fetch_app_info()
        await bot.db.get_guilds(bot.guilds)
        log.info(f"Logged in as {bot.user}\n")

    @staticmethod
    @bot.event
    async def on_disconnect() -> None:
        # log.warn("Disconnected!")
        pass

    @staticmethod
    @bot.event
    async def on_ready() -> None:
        log.info("Ready!\n")
        bot.set_ready()

    @staticmethod
    @bot.event
    async def on_message(message: discord.Message) -> None:
        if not bot.is_ready() or message.author.id == bot.user.id:
            return

        ctx = await bot.get_context(message)

        if str(ctx.channel.type) == "private":
            if message.content.lower() == "invite":
                return await bot.send_invite_link(message)

            log.info(f"DM from {ctx.author}: {message.content}")
            await bot.send_to_owner(
                embed=Embed(title=f"DM from {ctx.author}", description=message.content),
                sender=ctx.author.id,
            )
            return

        if ctx.command is not None:
            async with ctx.channel.typing():
                await bot.process_commands(message)

    @staticmethod
    @bot.event
    async def on_interaction(interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.application_command:
            return

        log.cmd(interaction, get_command_string(interaction), guild=interaction.guild or "N/A")

    @staticmethod
    @bot.event
    async def on_app_command_error(interaction: discord.Interaction, error: AppCommandError) -> None:
        error = getattr(error, "original", error)
        ignored = discord.NotFound, commands.BadArgument, commands.CheckFailure
        send_msg = exceptions.YtdlError, discord.app_commands.AppCommandError, discord.app_commands.CommandInvokeError

        tb = traceback.format_exception(
            error, value=error, tb=error.__traceback__
        )

        tb_msg = "\n".join(tb)[:1000] + "..."

        if type(error) in ignored:
            return

        log.cmd(interaction, f"Command error: {error}")

        if isinstance(error, send_msg):
            await interaction.response.send_message(embed=Embed(error))
            return

        embed = Embed("There was an error executing the command. Please contact the administrator.")

        await bot.send_response(interaction, embed=embed)

        embed = Embed(
            title="Traceback Exception",
            description=f"Command: ```{get_command_string(interaction)}``````py\n{tb_msg}```",
        )

        await bot.send_to_owner(embed=embed)

        raise error

    @staticmethod
    @bot.event
    async def on_guild_join(guild):
        log.info(f"Executing init for {guild}...")
        await Guild.get_instance(guild.id).create_default_collection()
        await bot.sync_command(guild)

    @staticmethod
    @bot.event
    async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.id == bot.user.id:
            player = Player.get_instance_from_guild(member.guild)

            if not after.channel:
                player.reset_timeout.start()
            elif player.reset_timeout.is_running():
                player.reset_timeout.cancel()

        guild = Guild.get_instance(member.guild.id)

        if before.channel != after.channel:
            log_channel = bot.get_channel(int(guild.get('channel.voice_log') or -1))

            # Check if the voice channel is not private
            role = member.guild.default_role
            before_readable = before.channel.permissions_for(role).view_channel if before.channel else False
            after_readable = after.channel.permissions_for(role).view_channel if after.channel else False

            msg = None

            if after.channel and before.channel and before_readable and after_readable:
                msg = f"**{member.mention}** has moved from **{before.channel.mention} to {after.channel.mention}**"
            elif after.channel and after_readable:
                msg = f"**{member.mention}** has connected to **{after.channel.mention}**"
            elif before_readable:
                msg = f"**{member.mention}** has disconnected from **{before.channel.mention}**"

            if log_channel and msg:
                embed = Embed(f":bust_in_silhouette:{msg}", timestamp=datetime.now())
                embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                await log_channel.send(embed=embed)

    @staticmethod
    @bot.event
    async def on_presence_update(before: discord.Member, after: discord.Member) -> None:
        if after.bot:
            return

        guild = Guild.get_instance(after.guild.id)
        log_channel = bot.get_channel(int(guild.get('channel.presence_log') or -1))

        embed = Embed(timestamp=datetime.now())
        embed.set_author(name=str(after), icon_url=after.display_avatar.url)

        if before.status != after.status:
            msg = f"**{before.mention}** is now **{after.status}**."
            embed.description = msg
        elif before.activities != after.activities:
            before_activity = before.activities and before.activities[-1]
            after_activity = after.activities and after.activities[-1]

            def get_image(
                activity: Union[discord.Spotify, discord.Game, discord.Activity]
            ) -> Optional[str]:
                if isinstance(activity, discord.Spotify):
                    return activity.album_cover_url
                elif isinstance(activity, discord.Activity):
                    return activity.large_image_url or activity.small_image_url
                return None

            embed.description = f"**{before.mention}** is"

            if isinstance(after_activity, discord.Spotify):
                if getattr(before_activity, "title", None) == after_activity.title:
                    return

                embed.set_thumbnail(get_image(after_activity))
                embed.add_field("Title", after_activity.title)
                embed.add_field("Artist", after_activity.artist)
            elif isinstance(after_activity, (discord.Activity, discord.Game)):
                if getattr(before_activity, "name", None) == after_activity.name:
                    return

                embed.set_thumbnail(get_image(after_activity))
                if getattr(after_activity, "details", None):
                    embed.add_field("Details", escape_markdown(after_activity.details))

            if isinstance(before_activity, discord.CustomActivity) and \
                isinstance(after_activity, discord.CustomActivity):
                embed.description += f" changed custom status from **{before_activity.name}** to **{after_activity.name}**."
            elif before_activity and (not after_activity or isinstance(after_activity, discord.CustomActivity)):
                embed.set_thumbnail(get_image(before_activity))
                embed.description += f" done {before_activity.type.name} **{before_activity.name}**."
                if hasattr(before_activity, 'start') and before_activity.start:
                    embed.add_field(
                        name="Time Elapsed",
                        value=format_seconds(
                            datetime.now(tz=timezone.utc).timestamp() - before_activity.start.timestamp()
                        ),
                    )
            else:
                embed.description += f" now {after_activity.type.name} **{after_activity.name}**."

        if log_channel and embed.description:
            embed.description = ":bust_in_silhouette:" + embed.description
            await log_channel.send(embed=embed)


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    bot.tree.on_error = Event.on_app_command_error
    await bot.add_cog(Event())
