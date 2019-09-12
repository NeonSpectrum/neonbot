import asyncio
import logging
import random

import discord
from addict import Dict

from .. import bot
from ..helpers.constants import FFMPEG_OPTIONS
from ..helpers.date import format_seconds
from ..helpers.utils import Embed
from . import Ytdl

log = logging.getLogger(__name__)


class Player:
    """
    Initializes player that handles play, playlist, messages,
    repeat, shuffle, autoplay.
    """

    def __init__(self, guild: discord.Guild):
        self.db = bot.db.get_guild(guild.id)
        self.config = self.db.config.music
        self.connection = None
        self.current_queue = 0
        self.queue = []
        self.shuffled_list = []
        self.disable_after = False
        self.messages = Dict(last_playing=None, last_finished=None, paused=None)

    @property
    def now_playing(self):
        return self.queue[self.current_queue]

    async def play(self, ctx):
        now_playing = self.now_playing

        if not now_playing.stream and now_playing.ytdl:
            await now_playing.ytdl.process_entry(now_playing)
            info = now_playing.ytdl.get_info()
            info.requested = now_playing.requested
            self.queue[self.current_queue] = now_playing = info

        if Ytdl.is_link_expired(now_playing.stream):
            log.warn(f"Link expired: {now_playing.title}")
            ytdl = await Ytdl().extract_info(now_playing.id)
            self.queue[self.current_queue] = now_playing = ytdl.get_info()
            log.info(f"Fetched new link for {now_playing.title}")

        try:
            song = discord.FFmpegPCMAudio(
                now_playing.stream, before_options=FFMPEG_OPTIONS
            )
            source = discord.PCMVolumeTransformer(song, volume=self.config.volume / 100)
        except discord.ClientException:
            msg = "Error while playing the song."
            log.exception(msg)
            return await ctx.send(msg)

        async def after(error):
            if error:
                log.warn(f"After play error: {error}")
            if not self.disable_after:
                await self.next(ctx)

        self.connection.play(
            source,
            after=lambda error: asyncio.run_coroutine_threadsafe(
                after(error), bot.loop
            ),
        )
        await self.playing_message(ctx)
        self.disable_after = False

    async def next(self, ctx, *, index=None, stop=False):
        await self.finished_message(ctx, delete_after=5 if stop else None)

        if stop or index is not None:
            self.disable_after = True
            self.connection.stop()

            if stop:
                return

            self.current_queue = index
            return await self.play(ctx)

        if (
            self.process_shuffle()
            or await self.process_autoplay()
            or self.process_repeat()
        ):
            await self.play(ctx)

    async def playing_message(self, ctx, delete_after=None):
        config = self.config
        now_playing = self.now_playing

        log.cmd(ctx, f"Now playing {now_playing.title}", user=now_playing.requested)

        if self.messages.last_playing:
            await self.messages.last_playing.delete()

        footer = [
            str(now_playing.requested),
            format_seconds(now_playing.duration) if now_playing.duration else "N/A",
            f"Volume: {config.volume}%",
            f"Repeat: {config.repeat}",
            f"Shuffle: {'on' if config.shuffle else 'off'}",
            f"Autoplay: {'on' if config.autoplay else  'off'}",
        ]

        embed = Embed(title=now_playing.title, url=now_playing.url)
        embed.set_author(
            name=f"Now Playing #{self.current_queue+1}",
            icon_url="https://i.imgur.com/SBMH84I.png",
        )
        embed.set_footer(
            text=" | ".join(footer), icon_url=now_playing.requested.avatar_url
        )

        self.messages.last_playing = await ctx.send(
            embed=embed, delete_after=delete_after
        )

    async def finished_message(self, ctx, delete_after=None):
        config = self.config
        now_playing = self.now_playing

        log.cmd(
            ctx, f"Finished playing {now_playing.title}", user=now_playing.requested
        )

        if self.messages.last_finished:
            await self.messages.last_finished.delete()

        footer = [
            str(now_playing.requested),
            format_seconds(now_playing.duration) if now_playing.duration else "N/A",
            f"Volume: {config.volume}%",
            f"Repeat: {config.repeat}",
            f"Shuffle: {'on' if config.shuffle else 'off'}",
            f"Autoplay: {'on' if config.autoplay else  'off'}",
        ]

        embed = Embed(title=now_playing.title, url=now_playing.url)
        embed.set_author(
            name=f"Finished Playing #{self.current_queue+1}",
            icon_url="https://i.imgur.com/SBMH84I.png",
        )
        embed.set_footer(
            text=" | ".join(footer), icon_url=now_playing.requested.avatar_url
        )

        self.messages.last_finished = await ctx.send(
            embed=embed, delete_after=delete_after
        )

    def process_repeat(self) -> bool:
        config = self.config

        if self.current_queue == len(self.queue) - 1:
            if config.repeat == "all":
                self.current_queue = 0
            elif config.repeat == "off":
                # reset queue to index 0 and stop playing
                self.current_queue = 0
                return
        elif config.repeat != "single":
            self.current_queue += 1

        return True

    def process_shuffle(self) -> bool:
        if not self.config.shuffle:
            return

        if len(self.shuffled_list) == len(self.queue):
            self.shuffled_list = [self.now_playing.id]
        elif self.now_playing.id not in self.shuffled_list:
            self.shuffled_list.append(self.now_playing.id)

        while True:
            index = random.randint(0, len(self.queue) - 1)
            if self.queue[index].id not in self.shuffled_list:
                self.current_queue = index
                return True

    async def process_autoplay(self) -> bool:
        if not self.config.autoplay or self.current_queue != len(self.queue) - 1:
            return

        current_queue = self.now_playing

        related_videos = await Ytdl.get_related_videos(current_queue.id)
        filtered_videos = []

        for video in related_videos:
            existing = (
                len([queue for queue in self.queue if queue.id == video.id.videoId]) > 0
            )
            if not existing:
                filtered_videos.append(video)

        video_id = filtered_videos[0].id.videoId

        ytdl = await Ytdl().extract_info(video_id)
        info = ytdl.get_info()
        self.add_to_queue(None, info, requested=bot.user)
        self.current_queue += 1

        return True

    def add_to_queue(self, ctx, data, requested=None):
        data.requested = requested or ctx.author
        self.queue.append(data)

    def update_config(self, key, value):
        database = self.db
        database.config.music[key] = value
        database.update_config().refresh_config()
        self.config = database.config.music
        return self.config
