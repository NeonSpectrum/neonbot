import traceback
from datetime import datetime
from io import BytesIO
from typing import Optional, Union
from typing import TYPE_CHECKING

import discord
import lavalink
from discord.app_commands import AppCommandError
from discord.ext import commands
from discord.utils import escape_markdown
from lavalink import Node, NodeConnectedEvent, listener

from neonbot.classes.chatgpt.chatgpt import ChatGPT
from neonbot.classes.discord_utils.embed import Embed
from neonbot.classes.gemini import GeminiChat
from neonbot.classes.player.ytmusic import YTMusic
from neonbot.classes.voice_events import VoiceEvents
from neonbot.env import OWNER_IDS
from neonbot.models.guild import GuildModel
from neonbot.utils import log
from neonbot.utils.functions import format_seconds, get_command_string, get_log_prefix, md_to_text, remove_ansi

if TYPE_CHECKING:
    from neonbot import NeonBot
    from neonbot.classes.player.player import Player


class Event(commands.Cog):
    def __init__(self, bot: 'NeonBot'):
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        await self.bot.fetch_app_info()
        log.info(f'Logged in as {self.bot.user}\n')

    @commands.Cog.listener()
    async def on_disconnect(self) -> None:
        # log.warn("Disconnected!")
        pass

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        log.info('Ready!\n')

        if not self.bot.is_ready():
            self.bot.start_listeners()
            await self.bot.join_autojoin_voice_channels()
            log.debug(f'YTMusic.get_account_info: {await YTMusic(self.bot).get_account_info()}')

        self.bot.set_ready()

    @listener(NodeConnectedEvent)
    async def on_node_connected(self, node: Node):
        log.info(f"Lavalink node '{node.name}' is ready!")

    async def on_message(self, message: discord.Message) -> None:
        if not self.bot.is_ready() or message.author.id == self.bot.user.id:
            return

        ctx = await self.bot.get_context(message)

        if ctx.channel.type == discord.ChannelType.private:
            if message.content.lower() == 'invite':
                await self.bot.send_invite_link(message)
                return

            log.info(f'DM from {ctx.author}: {message.content}')
            await self.bot.send_to_owner(embed=Embed(title=f'DM from {ctx.author}', description=message.content))
            return

        if await ChatGPT().create_thread(ctx):
            return

        if self.bot.user.mentioned_in(message):
            try:
                gemini_chat = GeminiChat(ctx)

                if not gemini_chat.get_prompt():
                    return

                async with ctx.channel.typing():
                    await gemini_chat.generate_content()
                    response = gemini_chat.get_response()

                    if len(response) > 2000:
                        response = md_to_text(response)
                        bot_message = await ctx.reply(
                            files=[
                                [discord.File(BytesIO(response.encode()), filename=gemini_chat.get_prompt() + '.txt')]
                                + gemini_chat.get_response_attachments()
                            ]
                        )
                    else:
                        bot_message = await ctx.reply(response, files=gemini_chat.get_response_attachments())

                cmds = gemini_chat.get_command_list()

                for cmd in cmds:
                    command, args = cmd

                    # Change message author so it won't recognize as bot
                    bot_message.author = message.author
                    bot_message.content = f'{self.bot.default_prefix}{command.name} {' '.join(args)}'

                    bot_ctx = await self.bot.get_context(bot_message)
                    bot_ctx.invoked_with = 'bot'

                    await self.bot.invoke(bot_ctx)
            except Exception as error:
                await ctx.reply(embed=Embed('Something went wrong.'))
                log.debug(error, exc_info=True)
                log.error(error, exc_info=True)
            finally:
                return

        if ctx.command is not None:
            async with ctx.channel.typing():
                await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context['NeonBot']):
        if ctx.interaction is not None:
            return

        log.cmd(ctx, get_command_string(ctx), guild=ctx.guild or 'N/A',
                user=ctx.guild.me if ctx.invoked_with == 'bot' else None)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction['NeonBot']):
        if interaction.type != discord.InteractionType.application_command:
            return

        ctx = await self.bot.get_context(interaction)
        log.cmd(ctx, get_command_string(ctx), guild=ctx.guild or 'N/A')

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id is not None:
            return True

        if interaction.user.id in OWNER_IDS:
            return True

        await interaction.response.send_message(
            embed=Embed('This personal app is restricted to the developer.'),
            ephemeral=True
        )
        return False

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Union[discord.Interaction['NeonBot'], commands.Context['NeonBot']], error: AppCommandError) -> None:
        if isinstance(ctx, discord.Interaction):
            ctx = await self.bot.get_context(ctx)

        error = getattr(error, 'original', error)
        ignored = (
            discord.NotFound,
            commands.BadArgument,
            commands.CheckFailure,
            discord.app_commands.CheckFailure,
            discord.ext.commands.MissingRequiredArgument
        )
        send_msg = (
            discord.app_commands.AppCommandError,
            discord.app_commands.CommandInvokeError,
            lavalink.errors.ClientError
        )

        tb = traceback.format_exception(error, value=error, tb=error.__traceback__)

        tb_msg = '\n'.join(tb)[:1000] + '...'

        if type(error) in ignored:
            return

        log.cmd(ctx, f'Command error: {error}')

        if isinstance(error, send_msg):
            embed = Embed(remove_ansi(str(error)))
        else:
            embed = Embed('There was an error executing the command. Please contact the administrator.')

        await ctx.send(embed=embed, ephemeral=True)

        embed = Embed(
            title='Traceback Exception',
            description=f'Command: ```{get_command_string(ctx)}``````py\n{tb_msg}```',
        )

        await self.bot.send_to_owner(embed=embed)

        raise error

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        log.info(f'Executing init for {guild}...')
        await GuildModel.create_default_collection(guild.id)
        await GuildModel.create_instance(guild.id)
        await self.bot.sync_command(guild)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        player: Player = await self.bot.create_player_instance(member.guild.id)
        server = GuildModel.get_instance(member.guild.id)

        if member.id == self.bot.user.id:
            if server.music.autojoin_channel_id is not None and after.channel is None:
                vc: discord.VoiceChannel = self.bot.get_channel(server.music.autojoin_channel_id)
                await player.connect(vc)
            return

        if player and player.ctx and player.ctx.voice_client and player.vc:
            voice_members = [member for member in player.vc.members if not member.bot]

            if any(voice_members):
                player.reset_timeout.cancel()
                if player.is_auto_paused:
                    await player.resume(requester=self.bot.user)
                    player.is_auto_paused = False
            else:
                if not player.paused and player.is_playing:
                    await player.pause(requester=self.bot.user)
                    player.is_auto_paused = True
                # if not player.reset_timeout.is_running():
                #     await player.reset_timeout.start()

        if member.bot:
            return

        connect_channel = self.bot.get_channel(int(server.channel_log.connect or -1))
        deafen_channel = self.bot.get_channel(int(server.channel_log.deafen or -1))
        mute_channel = self.bot.get_channel(int(server.channel_log.mute or -1))
        server_deafen_channel = self.bot.get_channel(int(server.channel_log.server_deafen or -1))
        server_mute_channel = self.bot.get_channel(int(server.channel_log.server_mute or -1))
        stream_channel = self.bot.get_channel(int(server.channel_log.stream or -1))
        video_channel = self.bot.get_channel(int(server.channel_log.video or -1))

        voice_events = VoiceEvents(member, before, after)

        if voice_events.is_channel_changed:
            embed = voice_events.get_channel_changed_message()

            if connect_channel and embed:
                await connect_channel.send(embed=embed)

        if deafen_channel and voice_events.is_self_deafen_changed:
            await deafen_channel.send(embed=voice_events.get_self_deafen_message())
        elif mute_channel and voice_events.is_self_muted_changed:
            await mute_channel.send(embed=voice_events.get_self_muted_message())
        elif server_deafen_channel and voice_events.is_server_deafen_changed:
            await server_deafen_channel.send(embed=voice_events.get_server_deafen_message())
        elif server_mute_channel and voice_events.is_server_muted_changed:
            await server_mute_channel.send(embed=voice_events.get_server_muted_message())
        elif stream_channel and voice_events.is_self_stream_changed:
            await stream_channel.send(embed=voice_events.get_self_stream_message())
        elif video_channel and voice_events.is_self_video_changed:
            await video_channel.send(embed=voice_events.get_self_video_message())

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        if after.bot:
            return

        server = GuildModel.get_instance(after.guild.id)
        status_log_channel = self.bot.get_channel(int(server.channel_log.status or -1))
        activity_log_channel = self.bot.get_channel(int(server.channel_log.activity or -1))

        if before.status != after.status:
            embed = Embed()
            embed.description = f'**{before.mention}** is now **{after.status}**.'

            if status_log_channel:
                embed.description = get_log_prefix() + embed.description
                try:
                    await status_log_channel.send(embed=embed)
                except discord.DiscordException:
                    pass
        elif before.activities != after.activities:
            before_activity = before.activities and before.activities[-1]
            after_activity = after.activities and after.activities[-1]

            def get_image(activity: Union[discord.Spotify, discord.Game, discord.Activity]) -> Optional[str]:
                if isinstance(activity, discord.Spotify):
                    return activity.album_cover_url
                elif isinstance(activity, discord.Activity):
                    return activity.large_image_url or activity.small_image_url
                return None

            embed = Embed(timestamp=datetime.now())
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            embed.description = f'**{before.mention}** is'

            if isinstance(after_activity, discord.Spotify):
                if getattr(before_activity, 'title', None) == after_activity.title:
                    return

                embed.set_thumbnail(get_image(after_activity))
                embed.add_field('Title', after_activity.title)
                embed.add_field('Artist', after_activity.artist)
            elif isinstance(after_activity, (discord.Activity, discord.Game)):
                if getattr(before_activity, 'name', None) == after_activity.name:
                    return

                embed.set_thumbnail(get_image(after_activity))
                if getattr(after_activity, 'details', None):
                    embed.add_field('Details', escape_markdown(after_activity.details))

            if (
                not after_activity
                and before_activity
                and before_activity.name == 'Custom Status'
                or not before_activity
                and after_activity
                and after_activity.name == 'Custom Status'
            ):
                return

            if (
                isinstance(before_activity, discord.CustomActivity)
                and isinstance(after_activity, discord.CustomActivity)
                and before_activity.name != after_activity.name
            ):
                embed.description += (
                    f' changed custom status from **{before_activity.name}** to **{after_activity.name}**.'
                )
            elif before_activity and not after_activity:
                embed.set_thumbnail(get_image(before_activity))
                embed.description += f' done {before_activity.type.name} **{before_activity.name}**.'
                if hasattr(before_activity, 'start') and before_activity.start:
                    embed.add_field(
                        name='Time Elapsed',
                        value=format_seconds(
                            datetime.now().timestamp() - before_activity.start.timestamp()
                        ),
                    )
            else:
                embed.description += f' now {after_activity.type.name} **{after_activity.name}**.'

            if activity_log_channel:
                embed.description = ':bust_in_silhouette:' + embed.description
                try:
                    await activity_log_channel.send(embed=embed)
                except discord.DiscordException:
                    pass


async def setup(bot: 'NeonBot') -> None:
    cog = Event(bot)
    bot.on_message = cog.on_message
    bot.tree.on_error = cog.on_command_error
    bot.tree.interaction_check = cog.interaction_check
    await bot.add_cog(Event(bot))
