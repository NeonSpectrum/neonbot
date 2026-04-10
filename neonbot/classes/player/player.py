from __future__ import annotations

import asyncio
import random
from typing import Dict, List, Optional, Union, cast
from typing import TYPE_CHECKING

import discord
from discord import VoiceChannel
from discord.ext import tasks, commands
from discord.ext.commands import Context
from discord.utils import find
from i18n import t
from lavalink import AudioTrack, DefaultPlayer, DeferredAudioTrack, LoadType, TrackEndEvent, TrackStartEvent
from ytmusicapi.exceptions import YTMusicError

from lib.lavalink_voice_client import LavalinkVoiceClient
from neonbot.classes.discord_utils.embed import Embed
from neonbot.classes.player.player_message_manager import PlayerMessageManager
from neonbot.classes.player.ytmusic import YTMusic
from neonbot.dataclasses import PlayerMessage
from neonbot.enums import Repeat, MessageType
from neonbot.models.guild import GuildModel
from neonbot.utils import log
from neonbot.utils.functions import clean_youtube_url, is_youtube_url, wait_until

if TYPE_CHECKING:
    from neonbot import NeonBot
    from neonbot.classes.lavalink.client import Client
    from lavalink import Node


class Player(DefaultPlayer):
    def __init__(self, guild_id: int, node: 'Node'):
        super().__init__(guild_id, node)

        # noinspection PyFinal
        self.client: 'Client' = node.manager.client
        self.bot: 'NeonBot' = self.client.bot

        self.settings = GuildModel.get_instance(self.guild_id)
        self.messager: PlayerMessageManager = PlayerMessageManager(self.bot, self.guild_id)
        self._track_event_lock = asyncio.Lock()

        self.ctx: Optional[Context] = None
        self.vc: Optional[VoiceChannel] = None
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

    @property
    def playlist(self) -> List[AudioTrack]:
        return self.shuffled_list if self.shuffle else self.track_list

    @property
    def autoplay(self) -> bool:
        return self.settings.music.autoplay

    @property
    def is_last_track(self) -> bool:
        return self.current_queue == len(self.playlist) - 1

    @autoplay.setter
    def autoplay(self, value) -> None:
        self.settings.music.autoplay = value
        self.bot.loop.create_task(self.settings.save_changes(False))

    def set_ctx(self, ctx: commands.Context['NeonBot']):
        self.ctx = ctx
        self.messager.set_ctx(ctx)

    async def handle_event(self, event):
        pass

    def set_loop(self, value: int) -> None:
        super().set_loop(value)
        self.settings.music.repeat = value
        self.bot.loop.create_task(self.settings.save_changes(False))
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
        self.bot.loop.create_task(self.settings.save_changes(False))
        self.messager.refresh_player_controls(embed=True)

    def set_autoplay(self, value: bool):
        self.autoplay = value
        self.messager.refresh_player_controls(embed=True)

    @tasks.loop(count=1)
    async def reset_timeout(self, timeout=60) -> None:
        await asyncio.sleep(timeout)

        await self.reset()

        msg = 'Player reset due to inactivity.'
        log.cmd(self.ctx, msg)
        await self.send_message(embed=Embed(msg))

    async def connect(self, voice_channel: discord.VoiceChannel = None):
        if self.ctx and self.ctx.guild.voice_client:
            if voice_channel and self.ctx.guild.voice_client.channel != voice_channel:
                self.vc = voice_channel
                await self.ctx.guild.me.move_to(voice_channel)
                log.cmd(self.ctx, t('music.player_connected', channel=self.vc))

            return

        self.vc = voice_channel or self.ctx.author.voice.channel
        await self.vc.connect(timeout=3, reconnect=True, self_deaf=True, cls=LavalinkVoiceClient)
        log.cmd(self.ctx, t('music.player_connected', channel=self.vc))

    async def disconnect(self, force=True, destroy=True, timeout=None) -> None:
        if self.is_connected and self.ctx.voice_client:
            try:
                voice_client = cast(LavalinkVoiceClient, self.ctx.voice_client)
                await asyncio.wait_for(voice_client.disconnect(force=force, destroy=destroy), timeout=timeout)
                self.vc = None
            except asyncio.TimeoutError:
                pass

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
            requester: int = 0, index: Optional[int] = None):
        track.extra['index'] = len(self.track_list)
        if requester:
            track.requester = requester
        self.track_list.append(track)

        if self.shuffle:
            index = random.randint(self.current_queue, len(self.shuffled_list))
            self.shuffled_list.insert(index, track)

        if self.current:
            self.messager.refresh_player_controls()

        if requester != self.bot.user.id:
            self.bot.loop.create_task(YTMusic(self.bot).like_song(track.identifier))

    def remove(self, index):
        if self.shuffle:
            self.shuffled_list[:] = [
                track for track in self.shuffled_list
                if track.extra.get('index') != index
            ]

        target_track: Optional[AudioTrack] = find(lambda track: track.extra.get('index') == index, self.track_list)

        if not target_track:
            raise IndexError

        removed_track = self.track_list.pop(target_track.extra.get('index'))

        # Adjust index on all tracks
        for index, track in enumerate(self.shuffled_list):
            if track.extra.get('index') > index:
                track.extra['index'] -= 1
        for index, track in enumerate(self.track_list):
            if track.extra.get('index') > index:
                track.extra['index'] -= 1

        return removed_track

    async def search_random(self):
        tracks = await YTMusic(self.bot).get_random_tracks()

        self.autoplay_list = self.filter_tracks_from_existing(tracks)

        track = self.autoplay_list.pop(0)
        await self.search(f"https://music.youtube.com/watch?v={track['id']}")

    async def search(self, query: str, *, send_message=True, requester=None):
        if not query.startswith(('http://', 'https://')):
            query = f'ytmsearch:{query}'
        elif is_youtube_url(query):
            query = clean_youtube_url(query)

        results = await self.node.get_tracks(query)

        load_type = results.load_type
        tracks = results.tracks
        embed = None

        log.debug(results)

        if load_type == LoadType.EMPTY:
            embed = Embed(t('music.no_songs_available'))

        if load_type == LoadType.ERROR:
            embed = Embed(t('music.search_error'))
            log.error(results.error.message)

        elif load_type == LoadType.PLAYLIST:
            count = 0
            for track in tracks:
                self.add(track, requester=requester or self.ctx.author.id)
                count += 1

            embed = Embed(
                t('music.added_multiple_to_queue', count=len(tracks)) + ' ' + t('music.added_failed',
                                                                                count=len(tracks) - count)
            )

        elif load_type == LoadType.TRACK or load_type == LoadType.SEARCH:
            track = tracks[0]

            self.add(track, requester=requester or self.ctx.author.id)

            embed = Embed(t('music.added_to_queue', queue=len(self.track_list), title=track.title, url=track.uri))

        if embed and send_message:
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
            if self.current_queue == len(self.playlist) - 1:  # move to last if end of playlist
                next_queue = 0
            else:
                next_queue = self.current_queue + 1  # just increment if not last
        elif self.loop == Repeat.SINGLE:  # repeat single
            pass
        elif self.autoplay and self.is_last_track:  # autoplay
            try:
                await self.process_autoplay(self.last_track)
            except YTMusicError:
                await self.send_message(embed=Embed('No related videos available.'))
                return
            next_queue = self.current_queue + 1
        elif self.loop == Repeat.OFF:  # repeat off
            if self.is_last_track:  # dont play if last
                return
            next_queue = self.current_queue + 1  # just increment if not last

        if next_queue is not None and 0 <= next_queue < len(self.playlist):
            self.current_queue = next_queue

        try:
            track = self.playlist[self.current_queue]
        except IndexError:
            log.error(f'Playlist length is {len(self.playlist)}. Current queue is {self.current_queue}')
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

        await self.stop()
        await self.disconnect(force=True, destroy=False, timeout=timeout)
        await self.messager.replace_all_to_compact()

        await self.bot.lavalink.player_manager.destroy(self.guild_id)

    async def process_autoplay(self, track: AudioTrack) -> None:
        try:
            if len(track.identifier) != 11:
                video_id = await YTMusic(self.bot).search(track.title)
            else:
                video_id = track.identifier

            if len(self.autoplay_list) == 0:
                log.debug(f'Searching related tracks from `{track.title}` [{video_id}].')
                related_tracks = await YTMusic(self.bot).get_related_tracks(video_id)
                log.debug('Found related tracks: ' + str(len(related_tracks)))

                if len(related_tracks) == 0:
                    log.debug('Related tracks are empty. Getting random tracks.')
                    related_tracks = await YTMusic(self.bot).get_random_tracks()
                    log.debug('Found random tracks: ' + str(len(related_tracks)))

                self.autoplay_list = self.filter_tracks_from_existing(related_tracks)
                log.debug('self.autoplay_list: ' + str(len(self.autoplay_list)))

            related_video = self.autoplay_list.pop(0)
        except (YTMusicError, IndexError) as error:
            log.debug(error, exc_info=True)
            raise YTMusicError(error)

        video_url = f"https://music.youtube.com/watch?v={related_video['id']}"
        await self.search(video_url, send_message=False, requester=self.bot.user.id)

    async def send_message(self, *args, **kwargs):
        return await self.ctx.channel.send(*args, **kwargs)

    def find_new_current_queue(self, track_list):
        for index, track in enumerate(track_list):
            if track.extra.get('index') == track_list[index].extra['index']:
                return index

        log.warn('Cannot find new current queue. Returning index 0')
        return 0

    def filter_tracks_from_existing(self, track_list):
        existing_ids = [i.identifier for i in self.track_list]
        return [i for i in track_list if i['id'] not in existing_ids]

    async def track_start_event(self, event: TrackStartEvent):
        async with self._track_event_lock:
            await wait_until(lambda: self.is_playing)
            await self.messager.send_message(PlayerMessage(
                type=MessageType.PLAYING,
                track=event.track,
                compact=False
            ))
            self.last_track = event.track

    async def track_end_event(self, event: TrackEndEvent):
        async with self._track_event_lock:
            player_message = self.messager.get_latest_message(MessageType.PLAYING)
            await self.messager.replace_to_finished_playing(player_message)

            if event.reason.may_start_next():
                await self.queue_next_song()

                if len(self.queue) == 0 and len(self.playlist) > 0:
                    await self.messager.replace_to_non_compact(player_message)

                await self.play()
