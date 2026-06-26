from __future__ import annotations

import asyncio
import random
from typing import Dict, List, Optional, Union, cast
from typing import TYPE_CHECKING

import discord
from discord import VoiceChannel
from discord.ext import tasks, commands
from discord.ext.commands import Context
from i18n import t
from lavalink import AudioTrack, DefaultPlayer, DeferredAudioTrack, LoadType, TrackEndEvent, TrackStartEvent
from ytmusicapi.exceptions import YTMusicError

from lib.lavalink_voice_client import LavalinkVoiceClient
from neonbot.discord_ui.embed import Embed
from neonbot.music.enums import PlayerMessage, MessageType, Repeat
from neonbot.music.player_message import PlayerMessageManager
from neonbot.music.ytmusic import YTMusicHelper
from neonbot.models.guild import GuildModel
from neonbot.utils import log
from neonbot.utils.functions import clean_youtube_url, is_youtube_url, wait_until

if TYPE_CHECKING:
    from neonbot import NeonBot
    from neonbot.music.lavalink_client import Client
    from lavalink import Node

MAX_MESSAGER_SIZE = 50


class Player(DefaultPlayer):
    def __init__(self, guild_id: int, node: 'Node'):
        super().__init__(guild_id, node)

        # noinspection PyFinal
        self.client: 'Client' = node.manager.client
        self.bot: 'NeonBot' = self.client.bot

        self.settings = GuildModel.get_instance(self.guild_id)
        self.messager: PlayerMessageManager = PlayerMessageManager(self.bot, self.guild_id)
        self._track_event_lock = asyncio.Lock()
        self.command_lock = asyncio.Lock()
        self.ytmusic = YTMusicHelper(self.bot)
        self._reconnecting = False

        self.ctx: Optional[Context['NeonBot']] = None
        self.voice_channel: Optional[VoiceChannel] = None
        self.voice_client: Optional[LavalinkVoiceClient] = None
        self.current: Optional[AudioTrack] = None
        self.current_queue = -1
        self.last_track: Optional[AudioTrack] = None
        self.track_list: List[AudioTrack] = []
        self.shuffled_list: List[AudioTrack] = []
        self.autoplay_list: List[dict] = []
        self.is_auto_paused = False

        self.set_autoplay(self.autoplay)
        self.set_shuffle(self.settings.music.shuffle)
        self.set_loop(self.settings.music.repeat)

    def save_settings(self):
        async def _save():
            try:
                await self.settings.save_changes(False)
            except Exception:
                log.exception(f'Guild {self.guild_id}: save_settings failed')
        self.bot.loop.create_task(_save())

    @property
    def playlist(self) -> List[AudioTrack]:
        return self.shuffled_list if self.shuffle else self.track_list

    @property
    def autoplay(self) -> bool:
        return self.settings.music.autoplay

    @property
    def is_last_track(self) -> bool:
        return self.current_queue == len(self.playlist) - 1

    @property
    def is_autojoin_enabled(self) -> bool:
        return self.settings.music.autojoin_channel_id is not None

    @autoplay.setter
    def autoplay(self, value) -> None:
        self.settings.music.autoplay = value
        self.save_settings()

    def set_ctx(self, ctx: commands.Context['NeonBot'], *, save_last_channel_id=True):
        self.ctx = ctx
        self.messager.set_channel(self.bot.get_channel(self.settings.music.channel_id) or ctx.channel)

        if save_last_channel_id:
            self.settings.music.last_channel_id = ctx.channel.id
            self.save_settings()

    async def set_default_ctx(self):
        if self.ctx:
            return

        channel = self.bot.get_channel(self.settings.music.channel_id or self.settings.music.last_channel_id)

        if channel:
            log.debug(f'Setting default ctx to {channel.name}.')

            try:
                async for message in channel.history(limit=100):
                    if message.author == self.bot.user:
                        ctx = await self.bot.get_context(message)
                        self.set_ctx(ctx, save_last_channel_id=False)
                        return
            except discord.Forbidden:
                log.warn(f'Cannot read history in channel {channel.id}')

        voice_channel = self.bot.get_channel(self.settings.music.autojoin_channel_id)

        if voice_channel and isinstance(voice_channel, discord.VoiceChannel):
            log.debug(f'Setting default ctx to {voice_channel.name}.')

            try:
                message = await voice_channel.send(t('music.autoplay_executing'))
                ctx = await self.bot.get_context(message)
                self.set_ctx(ctx, save_last_channel_id=False)
                await message.delete()
                return
            except (discord.Forbidden, discord.HTTPException) as e:
                log.warn(f'Cannot send message to voice channel {voice_channel.id}: {e}')

        if not self.ctx:
            log.error(f'Guild {self.guild_id}: Cannot set default ctx')

    def set_loop(self, value: int) -> None:
        super().set_loop(value)
        self.settings.music.repeat = value
        self.save_settings()
        self.messager.refresh_player_controls(embed=True)

    def set_shuffle(self, value: bool) -> None:
        if value:
            self.shuffled_list = random.sample(self.track_list, len(self.track_list))
            if len(self.shuffled_list) > 0:
                self.current_queue = self.find_new_current_queue(self.shuffled_list)
        else:
            self.shuffled_list = []
            if len(self.track_list) > 0:
                self.current_queue = self.find_new_current_queue(self.track_list)

        super().set_shuffle(value)
        self.settings.music.shuffle = value
        self.save_settings()
        self.messager.refresh_player_controls(embed=True)

    def set_autoplay(self, value: bool):
        self.autoplay = value
        self.messager.refresh_player_controls(embed=True)

    @tasks.loop(count=1)
    async def reset_timeout(self, timeout=60) -> None:
        await asyncio.sleep(timeout)

        await self.reset()

        msg = t('music.player_reset_inactivity')
        log.cmd(self.ctx, msg)
        await self.send_message(embed=Embed(msg))

    async def connect(self, voice_channel: discord.VoiceChannel = None):
        if self.voice_client:
            if voice_channel and self.ctx and self.ctx.guild.voice_client:
                if self.ctx.guild.voice_client.channel != voice_channel:
                    self.voice_channel = voice_channel
                    await self.ctx.guild.me.move_to(voice_channel)
                    log.cmd(self.ctx, t('music.player_connected', channel=self.voice_channel))
            return

        if not self.ctx:
            raise commands.CommandError('Player context not available')

        try:
            if not voice_channel and not self.ctx.author.voice:
                raise commands.CommandError(t('music.must_be_in_voice_channel'))

            self.voice_channel = voice_channel or self.ctx.author.voice.channel
            self.voice_client = await self.voice_channel.connect(
                timeout=5, reconnect=True, self_deaf=True, cls=LavalinkVoiceClient
            )
            log.cmd(self.ctx, t('music.player_connected', channel=self.voice_channel, guild=self.voice_channel.guild))
        except Exception:
            self.voice_channel = None
            self.voice_client = None
            raise

    async def disconnect(self, force=True, destroy=True, timeout=None) -> None:
        try:
            ctx_vc = self.ctx.voice_client if self.ctx else None
            if ctx_vc:
                voice_client = cast(LavalinkVoiceClient, ctx_vc)
                if timeout is not None:
                    await asyncio.wait_for(voice_client.disconnect(force=force, destroy=destroy), timeout=timeout)
                else:
                    await voice_client.disconnect(force=force, destroy=destroy)
        except asyncio.TimeoutError:
            log.warn(f'Guild {self.guild_id}: disconnect timed out')
        except Exception as e:
            log.warn(f'Guild {self.guild_id}: disconnect error: {e}')
        finally:
            self.voice_channel = None
            self.voice_client = None

    async def pause(self, requester: Union[discord.User, discord.ClientUser]):
        if not self.is_playing:
            return

        await self.set_pause(True)
        log.cmd(self.ctx, t('music.player_paused', user=requester.name))

        await self.send_message(embed=Embed(t('music.player_paused', user=requester.mention)))
        self.messager.refresh_player_controls()

    async def resume(self, requester: Union[discord.User, discord.ClientUser]):
        if not self.paused:
            return

        await self.set_pause(False)
        log.cmd(self.ctx, t('music.player_resumed', user=requester.name))

        await self.send_message(embed=Embed(t('music.player_resumed', user=requester.mention)))
        self.messager.refresh_player_controls()

    def add(self, track: Union[AudioTrack, 'DeferredAudioTrack', Dict[str, Union[Optional[str], bool, int]]],
            requester: int = 0):
        if requester:
            track.requester = requester
        self.track_list.append(track)

        if self.shuffle:
            insert_pos = random.randint(0, len(self.shuffled_list))
            self.shuffled_list.insert(insert_pos, track)

        if self.current:
            self.messager.refresh_player_controls()

        if requester != self.bot.user.id:
            self.bot.loop.create_task(self.ytmusic.like_song(track.identifier))

    def remove(self, index: int):
        playlist = self.playlist
        if index < 0 or index >= len(playlist):
            raise IndexError

        removed_track = playlist.pop(index)

        if self.shuffle:
            try:
                self.track_list.remove(removed_track)
            except ValueError:
                pass

        if index < self.current_queue:
            self.current_queue -= 1
        elif index == self.current_queue and self.current_queue >= len(self.playlist):
            self.current_queue = max(0, len(self.playlist) - 1)

        return removed_track

    async def search_random(self):
        tracks = await self.ytmusic.get_random_tracks()

        self.autoplay_list = self.filter_tracks_from_existing(tracks)

        if not self.autoplay_list:
            log.warn(f'Guild {self.guild_id}: search_random: no available tracks')
            return

        track = self.autoplay_list.pop(0)
        await self.search(f"https://music.youtube.com/watch?v={track['id']}")

    async def search(self, query: str, *, send_message=True, requester=None):
        if not query.startswith(('http://', 'https://')):
            query = f'ytmsearch:{query}'
        elif is_youtube_url(query):
            query = clean_youtube_url(query)

        try:
            results = await self.node.get_tracks(query)
        except Exception as error:
            log.error(f'Guild {self.guild_id}: Lavalink search failed: {error}')
            if send_message and self.ctx:
                await self.ctx.reply(embed=Embed(t('music.search_error')))
            return

        load_type = results.load_type
        tracks = results.tracks
        embed = None

        log.debug(results)

        if load_type == LoadType.EMPTY:
            embed = Embed(t('music.no_songs_available'))

        elif load_type == LoadType.ERROR:
            embed = Embed(t('music.search_error'))
            log.error(results.error.message)

        elif load_type == LoadType.PLAYLIST:
            for track in tracks:
                self.add(track, requester=requester or (self.ctx.author.id if self.ctx else self.bot.user.id))

            embed = Embed(t('music.added_multiple_to_queue', count=len(tracks)))

        elif load_type == LoadType.TRACK or load_type == LoadType.SEARCH:
            track = tracks[0]

            self.add(track, requester=requester or (self.ctx.author.id if self.ctx else self.bot.user.id))

            embed = Embed(t('music.added_to_queue', queue=len(self.track_list), title=track.title, url=track.uri))

        if embed and send_message and self.ctx:
            await self.ctx.reply(embed=embed)

    async def queue_next_song(self):
        if len(self.playlist) == 0:
            return

        next_queue = None

        # Priority: shuffle > repeat all > autoplay > repeat off

        if self.shuffle:  # shuffle
            if self.current_queue == len(self.playlist) - 1:
                next_queue = 0
            else:
                next_queue = self.current_queue + 1
        elif self.loop == Repeat.ALL:  # repeat all
            if self.current_queue == len(self.playlist) - 1:
                next_queue = 0
            else:
                next_queue = self.current_queue + 1
        elif self.loop == Repeat.SINGLE:  # repeat single
            pass
        elif self.autoplay and self.is_last_track:  # autoplay
            try:
                await self.process_autoplay(self.last_track)
            except YTMusicError:
                await self.send_message(embed=Embed(t('music.no_related_videos')))
                return
            next_queue = self.current_queue + 1
        elif self.loop == Repeat.OFF:  # repeat off
            if self.is_last_track:
                return
            next_queue = self.current_queue + 1

        if next_queue is not None and 0 <= next_queue < len(self.playlist):
            self.current_queue = next_queue

        try:
            track = self.playlist[self.current_queue]
        except IndexError:
            log.error(f'Guild {self.guild_id}: Playlist length is {len(self.playlist)}. Current queue is {self.current_queue}')
            return

        self.queue = [track]

    async def prev(self):
        if self.current_queue >= 1:
            self.current_queue -= 2  # Double minus since it will be increment on play()
        await self.skip()

    async def next(self):
        await self.skip()

    async def skip(self):
        await super().stop()
        await self.play_next()

    async def play_next(self):
        await self.queue_next_song()
        await self.play()

    async def stop(self):
        self.current = None
        self.current_queue = -1
        await super().stop()

    async def reset(self, timeout=None):
        self.track_list = []
        self.shuffled_list = []
        self.autoplay_list = []

        await self.stop()

        if self.is_autojoin_enabled:
            await self.messager.replace_all_to_compact()
            self.last_track = None
            self.is_auto_paused = False
            self.messager.clear()
        else:
            await self.messager.replace_all_to_compact()
            await self.disconnect(force=True, destroy=False, timeout=timeout)

    async def process_autoplay(self, track: AudioTrack) -> None:
        try:
            if len(track.identifier) != 11:
                video_id = await self.ytmusic.search(track.title)
            else:
                video_id = track.identifier

            if not video_id:
                raise YTMusicError('Could not find video ID for track')

            if len(self.autoplay_list) == 0:
                log.debug(f'Searching related tracks from `{track.title}` [{video_id}].')
                related_tracks = await self.ytmusic.get_related_tracks(video_id)
                log.debug('Found related tracks: ' + str(len(related_tracks)))

                if len(related_tracks) == 0:
                    log.debug('Related tracks are empty. Getting random tracks.')
                    related_tracks = await self.ytmusic.get_random_tracks()
                    log.debug('Found random tracks: ' + str(len(related_tracks)))

                self.autoplay_list = self.filter_tracks_from_existing(related_tracks)
                log.debug('self.autoplay_list: ' + str(len(self.autoplay_list)))

            if not self.autoplay_list:
                raise YTMusicError('No available tracks for autoplay')

            related_video = self.autoplay_list.pop(0)
        except (YTMusicError, IndexError) as error:
            log.debug(error, exc_info=True)
            raise YTMusicError(error)

        video_url = f"https://music.youtube.com/watch?v={related_video['id']}"
        await self.search(video_url, send_message=False, requester=self.bot.user.id)

    async def send_message(self, *args, **kwargs):
        if not self.ctx:
            return None
        return await self.ctx.channel.send(*args, **kwargs)

    def find_new_current_queue(self, track_list):
        if self.current:
            try:
                return track_list.index(self.current)
            except ValueError:
                pass

        log.warn(f'Guild {self.guild_id}: Cannot find new current queue. Returning index 0')
        return 0

    def filter_tracks_from_existing(self, track_list):
        existing_ids = [i.identifier for i in self.track_list]
        return [i for i in track_list if i['id'] not in existing_ids]

    def _trim_messager_data(self):
        if len(self.messager.data) > MAX_MESSAGER_SIZE:
            trimmed = self.messager.data[:len(self.messager.data) - MAX_MESSAGER_SIZE]
            self.messager.data = self.messager.data[len(self.messager.data) - MAX_MESSAGER_SIZE:]
            for pm in trimmed:
                if pm.message:
                    self.bot.loop.create_task(pm.message.delete(delay=0))

    async def track_start_event(self, event: TrackStartEvent):
        async with self._track_event_lock:
            result = await wait_until(lambda: self.is_playing, timeout=30)
            if result is None and not self.is_playing:
                log.warn(f'Guild {self.guild_id}: track never started playing')
                return
            await self.messager.send_message(PlayerMessage(
                type=MessageType.PLAYING,
                track=event.track,
                compact=False
            ))
            self.last_track = event.track

    async def track_end_event(self, event: TrackEndEvent):
        async with self._track_event_lock:
            self._trim_messager_data()

            player_message = self.messager.get_latest_message(MessageType.PLAYING)
            await self.messager.replace_to_finished_playing(player_message)

            if event.reason.may_start_next():
                await self.queue_next_song()

                if len(self.queue) == 0 and len(self.playlist) > 0:
                    await self.messager.replace_to_non_compact(player_message)

                await self.play()
