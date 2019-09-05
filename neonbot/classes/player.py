import random

import discord
from addict import Dict

from .. import bot
from ..helpers import log
from ..helpers.constants import FFMPEG_OPTIONS
from ..helpers.date import format_seconds
from ..helpers.utils import Embed
from . import YTDL


class Player:
    def __init__(self, guild_id):
        self.db = bot.db.get_guild(guild_id)
        self.config = self.db.config.music
        self.connection = None
        self.current_queue = 0
        self.queue = []
        self.shuffled_list = []
        self.disable_after = False
        self.messages = Dict(
            {"last_playing": None, "last_finished": None, "paused": None}
        )

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

        if YTDL.is_link_expired(now_playing.stream):
            log.info("Link expired:", now_playing.title)
            ytdl = await YTDL().extract_info(now_playing.id)
            self.queue[self.current_queue] = now_playing = ytdl.get_info()
            log.info("Fetched new link for", now_playing.title)

        try:
            song = discord.FFmpegPCMAudio(
                now_playing.stream, before_options=FFMPEG_OPTIONS
            )
            source = discord.PCMVolumeTransformer(song, volume=self.config.volume / 100)
        except discord.ClientException as e:
            log.warn(e)
            return await ctx.send("Error while playing the song.")

        async def after(error):
            if error:
                log.warn("After play error:", error)
            if not self.disable_after:
                await self.next(ctx)

        self.connection.play(
            source, after=lambda error: bot.loop.create_task(after(error))
        )
        await self.playing_message(ctx)
        self.disable_after = False

    async def next(self, ctx, *, index=None, stop=False):
        config = self.config

        await self.finished_message(ctx, delete_after=5 if stop else None)

        if stop or index is not None:
            self.disable_after = True
            self.connection.stop()

            if stop:
                return

            if len(self.queue) == index and self.current_queue == len(self.queue) - 1:
                if config.repeat == "off" and config.autoplay:
                    await self.process_autoplay(ctx)
                    self.current_queue += 1
                else:
                    self.current_queue = 0
            else:
                self.current_queue = index
            return await self.play(ctx)

        if config.shuffle or await self.process_repeat(ctx):
            if config.shuffle:
                self.current_queue = self.process_shuffle(ctx)
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

    async def process_repeat(self, ctx):
        config = self.config

        if self.current_queue == len(self.queue) - 1:
            if config.repeat == "all":
                self.current_queue = 0
            elif config.repeat == "off":
                if config.autoplay:
                    await self.process_autoplay(ctx)
                    self.current_queue += 1
                else:
                    # reset queue to index 0 and stop playing
                    self.current_queue = 0
                    return False
        elif config.repeat != "single":
            self.current_queue += 1

        return True

    def process_shuffle(self, ctx):
        if self.current_queue in self.shuffled_list:
            self.shuffled_list.append(self.current_queue)
        if len(self.shuffled_list) == len(self.queue):
            self.shuffled_list = [self.current_queue]
        while True:
            index = random.randint(0, len(self.queue) - 1)
            if index not in self.shuffled_list:
                return index

    async def process_autoplay(self, ctx):
        current_queue = self.now_playing

        related_videos = await YTDL.get_related_videos(current_queue.id)
        filtered_videos = []

        for video in related_videos:
            existing = (
                len([queue for queue in self.queue if queue.id == video.id.videoId]) > 0
            )
            if not existing:
                filtered_videos.append(video)

        video_id = filtered_videos[0].id.videoId

        ytdl = await YTDL().extract_info(video_id)
        info = ytdl.get_info()
        self.add_to_queue(ctx, info, requested=ctx.author)

    def add_to_queue(self, ctx, data, requested=None):
        data.requested = requested or ctx.author
        self.queue.append(data)

    def update_config(self, key, value):
        database = self.db
        database.config.music[key] = value
        database.update_config().refresh_config()
        self.config = database.config.music
        return self.config
