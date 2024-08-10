import traceback
from datetime import datetime, timezone
from io import BytesIO
from typing import Union, Optional

import discord
import yt_dlp.utils
from discord.app_commands import AppCommandError
from discord.ext import commands
from discord.utils import escape_markdown

from neonbot import bot
from neonbot.classes.chatgpt.chatgpt import ChatGPT
from neonbot.classes.embed import Embed
from neonbot.classes.gemini import GeminiChat
from neonbot.classes.player import Player
from neonbot.classes.voice_events import VoiceEvents
from neonbot.enums import PlayerState
from neonbot.models.guild import Guild
from neonbot.utils import log, exceptions
from neonbot.utils.functions import format_seconds, get_log_prefix, split_long_message, md_to_text, remove_ansi
from neonbot.utils.functions import get_command_string


class Event(commands.Cog):
    @staticmethod
    @bot.event
    async def on_connect() -> None:
        await bot.fetch_app_info()
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
        await bot.start_listeners()

    @staticmethod
    @bot.event
    async def on_message(message: discord.Message) -> None:
        if not bot.is_ready() or message.author.id == bot.user.id:
            return

        ctx = await bot.get_context(message)
        content = message.content

        if ctx.channel.type == discord.ChannelType.private:
            if message.content.lower() == "invite":
                return await bot.send_invite_link(message)

            log.info(f"DM from {ctx.author}: {message.content}")
            await bot.send_to_owner(
                embed=Embed(title=f"DM from {ctx.author}", description=message.content),
                sender=ctx.author.id,
            )
            return

        if await ChatGPT().create_thread(ctx):
            return

        if content.startswith('?? ') or content.startswith('??? '):
            gemini_chat = GeminiChat(ctx)

            if not gemini_chat.get_prompt():
                return

            await ctx.message.add_reaction('🤔')

            if content.startswith('?? '):
                gemini_chat.set_prompt_concise()

            async with ctx.channel.typing():
                await gemini_chat.generate_content(ctx)
                response = gemini_chat.get_response()

                if len(response) > 2000:
                    response = md_to_text(response)
                    await ctx.reply(file=discord.File(BytesIO(response.encode()), filename=gemini_chat.get_prompt() + '.txt'))
                else:
                    await ctx.reply(gemini_chat.get_response())

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
        ignored = discord.NotFound, commands.BadArgument, commands.CheckFailure, discord.app_commands.CheckFailure
        send_msg = (
            exceptions.YtdlError,
            discord.app_commands.AppCommandError,
            discord.app_commands.CommandInvokeError,
            yt_dlp.utils.YoutubeDLError
        )

        tb = traceback.format_exception(
            error, value=error, tb=error.__traceback__
        )

        tb_msg = "\n".join(tb)[:1000] + "..."

        if type(error) in ignored:
            return

        log.cmd(interaction, f"Command error: {error}")

        if isinstance(error, send_msg):
            embed = Embed(remove_ansi(error))
        else:
            embed = Embed("There was an error executing the command. Please contact the administrator.")

        await bot.send_response(interaction, embed=embed, ephemeral=True)

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
        await Guild.create_default_collection(guild.id)
        await Guild.create_instance(guild.id)
        await bot.sync_command(guild)

    @staticmethod
    @bot.event
    async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        player = Player.get_instance_from_guild(member.guild)

        # if member.id == bot.user.id:
        #     if before.channel and not after.channel:
        #         # Check if the bot was disconnected
        #         if player and player.connection and not player.connection.is_connected():
        #             await player.reset_timeout(timeout=10)
        #
        #     if not before.channel and after.channel:
        #         player.reset_timeout.cancel()
        #
        #     return

        if player and player.connection:
            voice_members = [
                member
                for member in player.connection.channel.members
                if not member.bot
            ]

            if any(voice_members):
                player.reset_timeout.cancel()
                if player.state == PlayerState.AUTO_PAUSED:
                    await player.resume(requester=bot.user)
            else:
                if player.connection.is_playing():
                    await player.pause(requester=bot.user, auto=True)
                if not player.reset_timeout.is_running():
                    await player.reset_timeout.start()

        server = Guild.get_instance(member.guild.id)

        connect_channel = bot.get_channel(int(server.channel_log.connect or -1))
        deafen_channel = bot.get_channel(int(server.channel_log.deafen or -1))
        mute_channel = bot.get_channel(int(server.channel_log.mute or -1))
        server_deafen_channel = bot.get_channel(int(server.channel_log.server_deafen or -1))
        server_mute_channel = bot.get_channel(int(server.channel_log.server_mute or -1))
        stream_channel = bot.get_channel(int(server.channel_log.stream or -1))
        video_channel = bot.get_channel(int(server.channel_log.video or -1))

        voice_events = VoiceEvents(member, before, after)

        if voice_events.is_channel_changed:
            embed = voice_events.get_channel_changed_message()

            if connect_channel and embed:
                await connect_channel.send(embed=embed)

        elif deafen_channel and voice_events.is_self_deafen_changed:
            await deafen_channel.send(embed=voice_events.get_self_deafen_message())
        elif mute_channel and voice_events.is_self_muted_changed:
            await mute_channel.send(embed=voice_events.get_self_muted_message())
        elif server_deafen_channel and voice_events.is_server_deafen_changed:
            await server_deafen_channel.send(embed=voice_events.get_server_deafen_message())
        elif server_mute_channel and voice_events.is_server_muted_changed:
            await server_mute_channel.send(embed=voice_events.get_server_muted_message())
        elif stream_channel and voice_events.is_self_stream_changed:
            await mute_channel.send(embed=voice_events.get_self_stream_message())
        elif video_channel and voice_events.is_self_video_changed:
            await mute_channel.send(embed=voice_events.get_self_video_message())

    @staticmethod
    @bot.event
    async def on_presence_update(before: discord.Member, after: discord.Member) -> None:
        if after.bot:
            return

        server = Guild.get_instance(after.guild.id)
        status_log_channel = bot.get_channel(int(server.channel_log.status or -1))
        activity_log_channel = bot.get_channel(int(server.channel_log.activity or -1))

        if before.status != after.status:
            embed = Embed()
            embed.description = f"**{before.mention}** is now **{after.status}**."

            if status_log_channel:
                embed.description = get_log_prefix() + embed.description
                await status_log_channel.send(embed=embed)
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

            embed = Embed(timestamp=datetime.now())
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
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

            if not after_activity and before_activity and before_activity.name == 'Custom Status' or \
                not before_activity and after_activity and after_activity.name == 'Custom Status':
                return

            if isinstance(before_activity, discord.CustomActivity) and \
                isinstance(after_activity, discord.CustomActivity) and \
                before_activity.name != after_activity.name:
                embed.description += f" changed custom status from **{before_activity.name}** to **{after_activity.name}**."
            elif before_activity and not after_activity:
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

            if activity_log_channel:
                embed.description = ":bust_in_silhouette:" + embed.description
                await activity_log_channel.send(embed=embed)


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    bot.tree.on_error = Event.on_app_command_error
    await bot.add_cog(Event())
