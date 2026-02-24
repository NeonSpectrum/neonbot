from __future__ import annotations

import asyncio
import random
from typing import Dict, List, Optional, Union

import discord
import ytmusicapi.exceptions
from discord import VoiceChannel, Message
from discord.ext import tasks
from discord.ext.commands import Context
from discord.utils import MISSING, find
from i18n import t
from lavalink import AudioTrack, DefaultPlayer, DeferredAudioTrack, LoadType, TrackEndEvent, TrackStartEvent

from lib.lavalink_voice_client import LavalinkVoiceClient
from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.classes.player_controls import PlayerControls
from neonbot.classes.ytmusic import YTMusic
from neonbot.enums import Repeat
from neonbot.models.guild import GuildModel
from neonbot.utils import log
from neonbot.utils.constants import ICONS
from neonbot.utils.exceptions import PlayerError
from neonbot.utils.functions import clean_youtube_url, format_milliseconds, is_youtube_url, wait_until


class Player(DefaultPlayer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settings = GuildModel.get_instance(self.guild_id)
        self.player_controls = PlayerControls(self.guild_id)
        self._track_start_event = asyncio.Event()
        self._track_end_event = asyncio.Event()
        self._track_start_event.set()
        self._track_end_event.set()

        self.ctx: Optional[Context] = None
        self.vc: Optional[VoiceChannel] = None
        self.current: Optional[AudioTrack] = None
        self.current_queue = -1
        self.last_track: Optional[AudioTrack] = None
        self.track_list: List[AudioTrack] = []
        self.shuffled_list: List[AudioTrack] = []
        self.autoplay_list: List[dict] = []
        self.messages: Dict[str, Optional[discord.Message]] = dict(
            playing=None,
            finished=None,
        )
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
        bot.loop.create_task(self.settings.save_changes(False))

    async def handle_event(self, event):
        pass

    def set_loop(self, value: int) -> None:
        super().set_loop(value)
        self.settings.music.repeat = value
        bot.loop.create_task(self.settings.save_changes(False))
        self.refresh_player_message(embed=True)

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
        bot.loop.create_task(self.settings.save_changes(False))
        self.refresh_player_message(embed=True)

    def set_autoplay(self, value: bool):
        self.autoplay = value
        self.refresh_player_message(embed=True)

    @tasks.loop(count=1)
    async def reset_timeout(self, timeout=60) -> None:
        await asyncio.sleep(timeout)

        await self.reset()

        msg = 'Player reset due to inactivity.'
        log.cmd(self.ctx, msg)
        await self.send_message(embed=Embed(msg))

    async def connect(self, voice_channel: discord.VoiceChannel = None):
        if self.ctx.guild.voice_client:
            if voice_channel and self.ctx.guild.voice_client.channel != voice_channel:
                self.vc = voice_channel
                await self.ctx.guild.me.move_to(voice_channel)
                log.cmd(self.ctx, t('music.player_connected', channel=self.vc))

            return

        self.vc = voice_channel or self.ctx.author.voice.channel
        await self.vc.connect(timeout=3, reconnect=True, self_deaf=True, cls=LavalinkVoiceClient)
        log.cmd(self.ctx, t('music.player_connected', channel=self.vc))

    async def disconnect(self, force=True, timeout=None) -> None:
        if self.is_connected and self.ctx.voice_client:
            try:
                await asyncio.wait_for(self.ctx.voice_client.disconnect(force=force), timeout=timeout)
                self.vc = None
            except asyncio.TimeoutError:
                pass

    async def pause(self, requester: discord.User):
        if not self.is_playing:
            return

        await self.set_pause(True)
        log.cmd(self.ctx, t('music.player_paused', user=requester.name))

        await self.send_message(embed=Embed(t('music.player_paused', user=requester.mention)))
        self.refresh_player_message()

    async def resume(self, requester: discord.User):
        if not self.paused:
            return

        await self.set_pause(False)
        log.cmd(self.ctx, t('music.player_resumed', user=requester.name))

        await self.send_message(embed=Embed(t('music.player_resumed', user=requester.mention)))
        self.refresh_player_message()

    def add(self, track: Union[AudioTrack, 'DeferredAudioTrack', Dict[str, Union[Optional[str], bool, int]]],
            requester: int = 0, index: Optional[int] = None):
        track.extra['index'] = len(self.track_list)
        if requester:
            track.requester = requester
        self.track_list.append(track)

        if self.shuffle:
            index = random.randint(self.current_queue, len(self.shuffled_list))
            self.shuffled_list.insert(index, track)

        self.refresh_player_message()

        if requester != bot.user.id:
            bot.loop.create_task(YTMusic.like_song(track.identifier))

    def remove(self, index):
        if self.shuffle:
            self.shuffled_list[:] = [
                track for track in self.shuffled_list
                if track.extra.get('index') != index
            ]

        target_index = find(lambda track: track.extra.get('index') == index, self.track_list)

        if not target_index:
            raise IndexError

        removed_track = self.track_list.pop(target_index.extra['index'])

        # Adjust index on all tracks
        for index, track in enumerate(self.shuffled_list):
            if track.extra.get('index') > index:
                track.extra['index'] -= 1
        for index, track in enumerate(self.track_list):
            if track.extra.get('index') > index:
                track.extra['index'] -= 1

        return removed_track

    async def prev(self):
        if self.current_queue >= 1:
            self.current_queue -= 2  # Double minus since it will be increment on play()
        await self.stop(wait=True)
        await self.play_next()

    async def next(self):
        await self.stop(wait=True)
        await self.play_next()

    async def search_random(self):
        tracks = await YTMusic.get_random_song()

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
        log.info(results)

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
            except PlayerError:
                await self.stop()
                await self.send_message(embed=Embed('No related videos available.'))
                return
            next_queue = self.current_queue + 1
        elif self.loop == Repeat.OFF:  # repeat off
            if self.current_queue == len(self.playlist) - 1:  # dont play if last
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

    async def play_next(self):
        await self.queue_next_song()
        await self.play()

    async def stop(self, wait=False):
        await super().stop()

        if wait:
            await self._track_end_event.wait()

    async def reset(self, timeout=None):
        self.track_list = []
        self.shuffled_list = []

        track = self.current

        await self.stop()
        await self.disconnect(force=True, timeout=timeout)

        if track:
            await self.send_finished_message(track)
        else:
            await self.clear_messages()

    async def process_autoplay(self, track: AudioTrack) -> None:
        try:
            if len(track.identifier) != 11:
                video_id = await YTMusic.search(track.title)
            else:
                video_id = track.identifier

            if len(self.autoplay_list) == 0:
                related_tracks = await YTMusic.get_related_tracks(video_id)

                if len(related_tracks) == 0:
                    related_tracks = await YTMusic.get_random_song()

                self.autoplay_list = self.filter_tracks_from_existing(related_tracks)

            related_video = self.autoplay_list.pop(0)
        except (ytmusicapi.exceptions.YTMusicServerError, IndexError) as error:
            log.debug(error, exc_info=True)
            raise PlayerError()

        video_url = f"https://music.youtube.com/watch?v={related_video['id']}"
        await self.search(video_url, send_message=False, requester=bot.user.id)

    async def send_message(self, *args, **kwargs):
        return await self.ctx.channel.send(*args, **kwargs)

    async def send_playing_message(self, track: AudioTrack) -> Message | None:
        log.cmd(
            self.ctx, t('music.now_playing.title', title=track.title), user=track.requester
        )

        await self.clear_messages()
        self.player_controls.initialize()

        return await self.send_message(
            embed=self.get_playing_embed(track), view=self.player_controls.get(), silent=True
        )

    async def send_finished_message(self, track: AudioTrack) -> Message | None:
        log.cmd(
            self.ctx,
            t('music.finished_playing.title', title=track.title),
            user=track.requester,
        )

        await self.clear_messages()

        return await self.send_message(
            embed=self.get_simplified_finished_message(track),
            silent=True,
        )

    async def clear_messages(self):
        if self.messages['finished']:
            await bot.delete_message(self.messages['finished'])
            await self.send_message(embed=self.get_simplified_finished_message(self.last_track), silent=True)

        await bot.delete_message(self.messages['playing'])
        self.messages['playing'] = None
        self.messages['finished'] = None

    def refresh_player_message(self, *, embed=False):
        if self.messages['playing']:
            bot.loop.create_task(bot.edit_message(
                self.messages['playing'],
                embed=self.get_playing_embed(self.current) if embed else MISSING,
                view=self.player_controls.get(),
            ))
        elif self.messages['finished']:
            bot.loop.create_task(bot.edit_message(
                self.messages['finished'],
                embed=self.get_finished_embed(self.last_track) if embed else MISSING,
                view=self.player_controls.get() if len(self.messages['finished'].components) > 0 else MISSING,
            ))

    def get_footer(self, track):
        return [
            bot.get_user(track.requester).display_name,
            format_milliseconds(track.duration),
            t('music.shuffle_footer', shuffle='on' if self.shuffle else 'off'),
            t('music.repeat_footer', repeat=Repeat(self.loop).name.lower()),
            t('music.autoplay_footer', autoplay='on' if self.autoplay else 'off'),
        ]

    def get_playing_embed(self, track: AudioTrack):
        return self.get_track_embed(track).set_author(
            name=t('music.now_playing.index', index=track.extra.get('index') + 1),
            icon_url=ICONS.get(track.source_name, ICONS.get('music')),
        )

    def get_finished_embed(self, track: AudioTrack):
        return self.get_track_embed(track).set_author(
            name=t('music.finished_playing.index', index=track.extra.get('index') + 1),
            icon_url=ICONS.get(track.source_name, ICONS.get('music')),
        )

    def get_track_embed(self, track: AudioTrack):
        footer = self.get_footer(track)
        embed = Embed(title=track.title, url=track.uri)
        embed.set_footer(text=' | '.join(footer), icon_url=bot.get_user(track.requester).display_avatar)

        return embed

    def get_simplified_finished_message(self, track: AudioTrack):
        formatted_title = f'[{track.title}]({track.uri})' if track.uri else track.title

        return Embed(f'{t("music.finished_playing.index", index=track.extra.get('index') + 1)}: {formatted_title}')

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
        if not self._track_start_event.is_set():
            return

        await self._track_end_event.wait()

        self._track_start_event.clear()

        await wait_until(lambda: self.is_playing, True)

        self.messages['playing'] = await self.send_playing_message(event.track)

        self._track_start_event.set()

    async def track_end_event(self, event: TrackEndEvent):
        if not self._track_end_event.is_set():
            return

        if event.track is None or len(self.playlist) == 0:
            return

        self._track_end_event.clear()

        self.current = None
        self.last_track = event.track

        message = await self.send_finished_message(event.track)

        if event.reason.may_start_next():
            await self.queue_next_song()

        if len(self.queue) == 0:
            self.messages['finished'] = await message.edit(
                embed=self.get_finished_embed(event.track),
                view=self.player_controls.get(),
            )

        if event.reason.may_start_next():
            await self.play()

        self._track_end_event.set()
