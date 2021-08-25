import asyncio
import logging
import random
from typing import List, Optional, Tuple, Union, cast

import discord
from addict import Dict
from discord.ext import commands, tasks

from ..helpers.constants import FFMPEG_OPTIONS
from ..helpers.date import format_seconds
from ..helpers.exceptions import YtdlError
from ..helpers.log import Log
from ..helpers.utils import plural
from . import Embed, EmbedChoices

log = cast(Log, logging.getLogger(__name__))


class Player:
    """
    Initializes player that handles play, playlist, messages,
    repeat, shuffle.
    """

    def __init__(self, ctx: commands.Context):
        from .spotify import Spotify
        from .ytdl import Ytdl

        self.ctx = ctx
        self.bot = ctx.bot
        self.db = self.bot.db.get_guild(ctx.guild.id)
        self.config = self.db.config.music
        self.spotify = Spotify()
        self.ytdl = Ytdl()

        self.load_defaults()

        self._load_music_cache()

    def load_defaults(self) -> None:
        self.connection: discord.VoiceClient = None
        self.last_voice_channel: discord.VoiceChannel = None
        self.current_queue = 0
        self.queue: List[Dict] = []
        self.shuffled_list: List[str] = []
        self.messages = Dict(
            last_playing=None, last_finished=None, paused=None, auto_paused=None
        )
        self.timeout_pause = False

    def _load_music_cache(self) -> None:
        cache = self.bot._music_cache.get(str(self.ctx.guild.id))
        if cache:
            self.current_queue = cache.current_queue
            self.queue = cache.queue
            for queue in self.queue:
                if queue.requested:
                    queue.requested = self.bot.get_user(queue.requested)

    @property
    def now_playing(self) -> Dict:
        return (
            self.queue[self.current_queue]
            if self.current_queue < len(self.queue)
            else Dict()
        )

    async def stop(self) -> None:
        await self.next(stop=True)

        if self.connection:
            await self.connection.disconnect()

        self.current_queue = 0

    async def reset(self) -> None:
        await asyncio.gather(
            self.bot.delete_message(self.messages.last_playing),
            self.bot.delete_message(self.messages.last_finished),
            self.bot.delete_message(self.messages.paused),
            self.bot.delete_message(self.messages.auto_paused)
        )

        await self.next(stop=True)

        self.load_defaults()

        if self.connection:
            await self.connection.disconnect()


    @tasks.loop(count=1)
    async def reset_timeout(self) -> None:
        await asyncio.sleep(60 * 10)

        await self.bot.delete_message(self.messages.auto_paused)
        await self.reset()

        msg = "Player has been reset due to timeout."
        log.cmd(self.ctx, msg)
        await self.ctx.send(embed=Embed(msg))

    async def on_member_leave(self):
        if not self.connection.is_playing(): return self.reset()

        msg = "Player paused and will reset after 10 minutes if no one will listen :("
        log.cmd(self.ctx, msg, channel=self.last_voice_channel, user="N/A")
        self.messages.auto_paused = await self.ctx.send(embed=Embed(msg))
        if self.connection.is_playing(): self.connection.pause()
        self.reset_timeout.start()

    async def on_member_join(self):
        if not self.reset_timeout.is_running(): return

        await self.bot.delete_message(self.messages.auto_paused)
        self.messages.auto_paused = None
        if self.connection.is_paused(): self.connection.resume()
        self.reset_timeout.cancel()

    async def play(self) -> None:
        now_playing = self.now_playing

        if not now_playing.stream:
            info = await self.ytdl.process_entry(now_playing)
            info = self.ytdl.parse_info(info)
            info.requested = now_playing.requested
            self.queue[self.current_queue] = now_playing = info

        if self.ytdl.is_link_expired(now_playing.stream):
            log.warn(f"Link expired: {now_playing.title}")
            info = await self.ytdl.extract_info(now_playing.id)
            self.queue[self.current_queue] = now_playing = self.ytdl.parse_info(info)
            log.info(f"Fetched new link for {now_playing.title}")

        try:
            song = discord.FFmpegPCMAudio(
                now_playing.stream, before_options=None if not now_playing.is_live else FFMPEG_OPTIONS
            )
            source = discord.PCMVolumeTransformer(song, volume=self.config.volume / 100)
        except discord.ClientException:
            msg = "Error while playing the song."
            log.exception(msg)
            await self.ctx.send(embed=Embed(msg))

        def after(error: Exception) -> None:
            if error:
                log.warn(f"After play error: {error}")
            self.bot.loop.create_task(self.next())

        self.connection.play(source, after=after)
        await self.playing_message()


    async def next(self, *, index: int = -1, stop: bool = False) -> None:
        if not stop or (stop and self.connection.is_playing()):
            await self.finished_message(delete_after=5 if stop else None)

        if stop or index != -1:
            if self.connection._player:
                self.connection._player.after = None

            self.connection.stop()

            if stop:
                await self.connection.disconnect()
                await self.bot.delete_message(self.messages.last_playing)
                return

            if index < len(self.queue):
                self.current_queue = index
                await self.play()
                return

            self.current_queue = index - 1

        if (
            self.process_shuffle()
            or self.process_repeat()
        ):
            await self.play()
        else:
            await self.connection.disconnect()

    async def playing_message(self, *, delete_after: Optional[int] = None) -> None:
        config = self.config
        now_playing = self.now_playing

        if not now_playing:
            return

        log.cmd(
            self.ctx, f"Now playing {now_playing.title}", user=now_playing.requested
        )

        await self.bot.delete_message(self.messages.last_playing)

        footer = [
            str(now_playing.requested),
            format_seconds(now_playing.duration) if now_playing.duration else "N/A",
            f"Volume: {config.volume}%",
            f"Repeat: {config.repeat}",
            f"Shuffle: {'on' if config.shuffle else 'off'}"
        ]

        embed = Embed(title=now_playing.title, url=now_playing.url)
        embed.set_author(
            name=f"Now Playing #{self.current_queue+1}",
            icon_url="https://i.imgur.com/SBMH84I.png",
        )
        embed.set_footer(
            text=" | ".join(footer), icon_url=now_playing.requested.avatar_url
        )

        self.messages.last_playing = await self.ctx.send(
            embed=embed, delete_after=delete_after
        )

    async def finished_message(self, *, delete_after: Optional[int] = None) -> None:
        config = self.config
        now_playing = self.now_playing

        if not now_playing:
            return

        log.cmd(
            self.ctx,
            f"Finished playing {now_playing.title}",
            user=now_playing.requested,
        )

        await self.bot.delete_message(self.messages.last_finished)

        footer = [
            str(now_playing.requested),
            format_seconds(now_playing.duration) if now_playing.duration else "N/A",
            f"Volume: {config.volume}%",
            f"Repeat: {config.repeat}",
            f"Shuffle: {'on' if config.shuffle else 'off'}",
        ]

        embed = Embed(title=now_playing.title, url=now_playing.url)
        embed.set_author(
            name=f"Finished Playing #{self.current_queue+1}",
            icon_url="https://i.imgur.com/SBMH84I.png",
        )
        embed.set_footer(
            text=" | ".join(footer), icon_url=now_playing.requested.avatar_url
        )

        self.messages.last_finished = await self.ctx.send(
            embed=embed, delete_after=delete_after
        )

    def process_repeat(self) -> bool:
        config = self.config
        is_last = self.current_queue == len(self.queue) - 1

        if is_last and config.repeat == "all":
            self.current_queue = 0
        elif is_last and config.repeat == "off":
            # reset queue to index 0 and stop playing
            self.current_queue += 1
            return False
        elif config.repeat != "single":
            self.current_queue += 1

        return True

    def process_shuffle(self) -> bool:
        if not self.config.shuffle or len(self.queue) == 0:
            return False

        if self.now_playing.id not in self.shuffled_list:
            self.shuffled_list.append(self.now_playing.id)

        counter = 0

        while True:
            if len(self.shuffled_list) >= len(self.queue) or counter >= 5:
                self.shuffled_list = [self.now_playing.id]

            index = random.randint(0, len(self.queue) - 1)
            if self.queue[index].id not in self.shuffled_list or len(self.queue) <= 1:
                self.current_queue = index
                return True

            counter += 1

    async def process_youtube(
        self, ctx: commands.Context, keyword: str, *, ytdl_list: Optional[list] = None
    ) -> Tuple[Union[Dict, List], discord.Embed]:
        loading_msg = await self.ctx.send(embed=Embed("Loading..."))

        if ytdl_list is None:
            ytdl_list = await self.ytdl.extract_info(keyword)

        info = Dict()
        embed: discord.Embed

        await self.bot.delete_message(loading_msg)

        if isinstance(ytdl_list, list):
            info = []
            for entry in ytdl_list:
                if entry.title != "[Deleted video]":
                    entry.url = f"https://www.youtube.com/watch?v={entry.id}"
                    info.append(entry)

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

    async def process_spotify(self, ctx: commands.Context, url: str) -> Tuple[Dict, discord.Embed]:
        result = self.spotify.parse_url(url)

        if not result:
            return await self.ctx.send(
                embed=Embed("Invalid spotify url."), delete_after=5
            )

        if result.type == "playlist":
            error = 0

            processing_msg = await self.ctx.send(
                embed=Embed("Converting to youtube playlist. Please wait...")
            )
            playlist = await self.spotify.get_playlist(result.id)
            ytdl_list = []

            for item in playlist:
                name = item.track.name
                artist = item.track.artists[0].name

                info = await self.ytdl.create({"default_search": "ytsearch1"}).extract_info(f"{artist} {name} lyrics")

                if len(info) == 0:
                    error += 1
                    continue

                ytdl_list.append(info[0])

            await self.bot.delete_message(processing_msg)

            info, embed = await self.process_youtube(ctx, "", ytdl_list=ytdl_list)

            if error > 0:
                embed = Embed(f"Added {plural(len(ytdl_list), 'song', 'songs')} to queue. {error} failed to load.")

            return info, embed

        else:
            track = await self.spotify.get_track(result.id)
            return await self.process_search(f"{track.artists[0].name} {track.name} lyrics", force_choice=0)

    async def process_search(
        self, keyword: str, *, force_choice: Optional[int] = None
    ) -> Tuple[Dict, discord.Embed]:
        msg = await self.ctx.send(embed=Embed("Searching..."))

        try:
            extracted = await self.ytdl.extract_info(keyword)
            ytdl_choices = self.ytdl.parse_choices(extracted)
        except YtdlError:
            await self.ctx.send(embed=Embed("No songs available."), delete_after=10)
            return Dict(), Embed()
        finally:
            await self.bot.delete_message(msg)

        if force_choice is None:
            embed_choices = await EmbedChoices(self.ctx, ytdl_choices).build()
            choice = embed_choices.value
            if choice < 0:
                return Dict(), Embed()
        else:
            choice = force_choice

        info = await self.ytdl.process_entry(extracted[choice])
        info = self.ytdl.parse_info(info)
        embed = Embed(
            title=f"{'You have selected #{choice+1}.' if force_choice else'' }Adding song to queue #{len(self.queue)+1}",
            description=info.title,
        )

        return info, embed

    def add_to_queue(self, data: Union[List, Dict], *, requested: discord.User = None) -> None:
        if not isinstance(data, list):
            data = [data]

        for info in data:
            info.requested = requested or self.ctx.author
            self.queue.append(info)

    def update_config(self, key: str, value: Union[str, int]) -> Dict:
        database = self.db
        database.config.music[key] = value
        database.update().refresh()
        self.config = database.config.music
        return self.config
