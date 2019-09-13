import logging
import random

import discord
from addict import Dict

from .. import bot
from ..helpers.constants import FFMPEG_OPTIONS
from ..helpers.date import format_seconds
from ..helpers.utils import Embed, embed_choices, plural
from . import Spotify, Ytdl

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
        self.messages = Dict(last_playing=None, last_finished=None, paused=None)
        self.ytdl = Ytdl()

    @property
    def now_playing(self):
        return self.queue[self.current_queue]

    async def play(self, ctx):
        now_playing = self.now_playing

        if not now_playing.stream:
            info = await self.ytdl.process_entry(now_playing)
            info = self.ytdl.parse_info(info)
            info.requested = now_playing.requested
            self.queue[self.current_queue] = now_playing = info

        if Ytdl.is_link_expired(now_playing.stream):
            log.warn(f"Link expired: {now_playing.title}")
            info = await self.ytdl.extract_info(now_playing.id)
            self.queue[self.current_queue] = now_playing = self.ytdl.parse_info(info)
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

        def after(error):
            if error:
                log.warn(f"After play error: {error}")
            bot.loop.create_task(self.next(ctx))

        self.connection.play(source, after=after)
        await self.playing_message(ctx)

    async def next(self, ctx, *, index=None, stop=False):
        await self.finished_message(ctx, delete_after=5 if stop else None)

        if stop or index is not None:
            if self.connection._player:
                self.connection._player.after = None
            self.connection.stop()

            if stop:
                if self.messages.last_playing:
                    try:
                        await self.messages.last_playing.delete()
                    except discord.NotFound:
                        pass
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
            try:
                await self.messages.last_playing.delete()
            except discord.NotFound:
                pass

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
            try:
                await self.messages.last_finished.delete()
            except discord.NotFound:
                pass

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

        info = await self.ytdl.extract_info(video_id)
        info = self.ytdl.parse_info(info)
        self.add_to_queue(None, info, requested=bot.user)
        self.current_queue += 1

        return True

    async def process_youtube(self, ctx, keyword, *, ytdl_list=None):
        loading_msg = await ctx.send(embed=Embed("Loading..."))

        if ytdl_list is None:
            ytdl_list = await self.ytdl.extract_info(keyword)

        info = embed = None

        await loading_msg.delete()

        if isinstance(ytdl_list, list):
            for entry in ytdl_list:
                if entry.title != "[Deleted video]":
                    entry.url = f"https://www.youtube.com/watch?v={entry.id}"
                    self.add_to_queue(ctx, entry)

            embed = Embed(f"Added {plural(len(ytdl_list), 'song', 'songs')} to queue.")
        elif ytdl_list:
            info = self.ytdl.parse_info(ytdl_list)
            embed = Embed(
                title=f"Added song to queue #{len(self.queue)+1}",
                description=info.title,
            )
        else:
            embed = Embed("Song failed to load.")

        return info, embed

    async def process_spotify(self, ctx, url):
        spotify = Spotify()
        result = spotify.parse_url(url)

        if not result:
            return await ctx.send(embed=Embed("Invalid spotify url."), delete_after=5)

        if result.type == "playlist":
            processing_msg = await ctx.send(
                embed=Embed("Converting to youtube playlist. Please wait...")
            )
            playlist = await spotify.get_playlist(result.id)
            ytdl_list = []

            for items in playlist.tracks["items"]:
                name = items.track.name
                artist = items.track.artists[0].name

                info = await Ytdl({"default_search": "ytsearch1"}).extract_info(
                    f"{artist} {name} lyrics"
                )
                ytdl_list.append(info[0])

            await processing_msg.delete()

            return await self.process_youtube(ctx, None, ytdl_list=ytdl_list)
        else:
            track = await spotify.get_track(result.id)
            return await self.process_search(
                ctx, f"{track.artists[0].name} {track.name} lyrics", force_choice=0
            )

    async def process_search(self, ctx, keyword, *, force_choice=None):
        msg = await ctx.send(embed=Embed("Searching..."))
        extracted = await self.ytdl.extract_info(keyword)
        ytdl_choices = self.ytdl.parse_choices(extracted)
        await msg.delete()
        if len(ytdl_choices) == 0:
            return await ctx.send(embed=Embed("No songs available."))
        if force_choice is None:
            choice = await embed_choices(ctx, ytdl_choices)
            if choice < 0:
                return
        else:
            choice = force_choice
        info = await self.ytdl.process_entry(extracted[choice])
        info = self.ytdl.parse_info(info)
        if not info:
            await ctx.send(
                embed=Embed(
                    "Video not available or rate limited due to many song requests. Try again later."
                ),
                delete_after=10,
            )
            return
        embed = Embed(
            title=f"{'You have selected #{choice+1}.' if force_choice else'' }Adding song to queue #{len(self.queue)+1}",
            description=info.title,
        )

        return info, embed

    def add_to_queue(self, ctx, data, requested=None):
        data.requested = requested or ctx.author
        self.queue.append(data)

    def update_config(self, key, value):
        database = self.db
        database.config.music[key] = value
        database.update_config().refresh_config()
        self.config = database.config.music
        return self.config
