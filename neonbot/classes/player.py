import asyncio
import logging
import random
from typing import List, Optional, Union, Dict, cast

import discord
from discord.ext import commands, tasks
from discord.utils import MISSING

from .embed import Embed, EmbedChoices
from .player_controls import PlayerControls
from .spotify import Spotify
from .ytdl import Ytdl
from ..helpers.constants import FFMPEG_OPTIONS
from ..helpers.date import format_seconds
from ..helpers.exceptions import YtdlError
from ..helpers.log import Log
from ..helpers.utils import plural

log = cast(Log, logging.getLogger(__name__))


class Player:
    """
    Initializes player that handles play, playlist, messages,
    repeat, shuffle.
    """

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.bot = ctx.bot
        self.db = self.bot.db.get_guild(ctx.guild.id)
        self.spotify = Spotify(self.bot)
        self.ytdl = Ytdl(self.bot)
        self.player_controls = PlayerControls(self)
        self.after = None

        self.load_default()

    def load_default(self) -> None:
        self.connection: Optional[discord.VoiceClient] = None
        self.last_voice_channel: Optional[discord.VoiceChannel] = None
        self.current_queue = 0
        self.queue: List[Optional[dict]] = []
        self.shuffled_list: List[int] = []
        self.messages: Dict[str, Optional[discord.Message]] = dict(
            last_playing=None,
            last_finished=None,
            paused=None,
            resumed=None,
            auto_paused=None,
            repeat=None,
            shuffle=None
        )
        self.timeout_pause = False
        self.previous_track = None
        self.track_list: List[int] = [0]

    @property
    def config(self):
        return self.db.get('music')

    @property
    def is_latest_track(self):
        return self.current_queue == len(self.track_list) - 1

    @property
    def now_playing(self) -> Union[dict, None]:
        try:
            return {
                "index": self.track_list[self.current_queue] + 1,
                **self.queue[self.track_list[self.current_queue]]
            }
        except IndexError:
            return None

    @now_playing.setter
    def now_playing(self, value) -> None:
        try:
            self.queue[self.track_list[self.current_queue]] = value
        except IndexError:
            pass

    async def stop(self) -> None:
        await self.next(stop=True)

        self.current_queue = 0

    async def reset(self) -> None:
        await self.next(stop=True)
        await self.bot.delete_message(*[self.messages[key] for key in self.messages])

        self.load_default()

    async def disconnect(self) -> None:
        if self.connection and self.connection.is_connected():
            await self.connection.disconnect()

    async def repeat(self, mode) -> None:
        self.update_config("repeat", mode)
        await self.bot.delete_message(self.messages['repeat'])
        self.messages['repeat'] = await self.ctx.send(embed=Embed(f"Repeat changed to {mode}."), delete_after=5)
        await self.refresh_player_message(embed=True)

    async def shuffle(self) -> None:
        self.update_config("shuffle", not self.config['shuffle'])
        await self.bot.delete_message(self.messages['shuffle'])
        self.messages['shuffle'] = await self.ctx.send(
            embed=Embed(f"Shuffle is set to {'enabled' if self.config['shuffle'] else 'disabled'}."),
            delete_after=5,
        )
        await self.refresh_player_message(embed=True)

    async def pause(self):
        if self.connection.is_paused():
            return

        self.connection.pause()
        log.cmd(self.ctx, "Player paused.")

        await self.bot.delete_message(self.messages['paused'], self.messages['resumed'])
        self.messages['paused'] = await self.ctx.send(
            embed=Embed(f"Player paused. `{self.ctx.prefix}resume` to resume.")
        )
        await self.refresh_player_message()

    async def resume(self):
        if self.connection.is_playing():
            return

        self.connection.resume()
        log.cmd(self.ctx, "Player resumed.")

        await self.bot.delete_message(self.messages['paused'], self.messages['resumed'])
        self.messages['resumed'] = await self.ctx.send(embed=Embed("Player resumed."), delete_after=5)
        await self.refresh_player_message()

    async def volume(self, volume: int):
        self.connection.source.volume = volume / 100
        self.update_config("volume", volume)
        await self.refresh_player_message(embed=True)

    async def play(self) -> None:
        if not self.connection or not self.connection.is_connected():
            return

        try:
            if not self.now_playing.get('stream'):
                info = await self.ytdl.process_entry(self.now_playing)
                info = self.ytdl.parse_info(info)
                self.now_playing = {**self.now_playing, **info}

            song = discord.FFmpegPCMAudio(
                self.now_playing['stream'],
                before_options=None if not self.now_playing['is_live'] else FFMPEG_OPTIONS,
            )
            source = discord.PCMVolumeTransformer(song, volume=self.config['volume'] / 100)

            def after(error: Exception) -> None:
                if error:
                    log.warning(f"After play error: {error}")
                if self.after:
                    self.bot.loop.create_task(self.after())

            self.after = self.next
            self.connection.play(source, after=after)

        except Exception as e:
            msg = "Error while playing the song."
            log.exception(msg, e)
            await self.ctx.send(embed=Embed(msg))

        await self.playing_message()

    async def next(self, *, index: Optional[int] = None, stop: bool = False) -> None:
        self.after = None

        if self.connection.is_playing():
            self.connection.stop()

        await self.finished_message()

        if stop:
            await self.connection.disconnect()
            return

        if index is not None:
            self.track_list.append(index)
            self.current_queue = len(self.track_list) - 1
            await self.play()
            return

        if not self.is_latest_track:
            self.current_queue += 1
        elif not (self.process_shuffle() or self.process_repeat()):
            return

        await self.play()

    async def playing_message(self, *, delete_after: Optional[int] = None) -> None:
        if not self.now_playing:
            return

        log.cmd(self.ctx, f"Now playing {self.now_playing['title']}", user=self.now_playing['requested'])

        await self.clear_playing_messages()
        self.player_controls.initialize()

        self.messages['last_playing'] = await self.ctx.send(
            embed=self.get_playing_embed(), view=self.player_controls.get(), delete_after=delete_after
        )
        self.previous_track = self.now_playing

    async def finished_message(self, *, delete_after: Optional[int] = None) -> None:
        if not self.previous_track:
            return

        log.cmd(
            self.ctx,
            f"Finished playing {self.previous_track['title']}",
            user=self.previous_track['requested'],
        )

        await self.clear_playing_messages()
        self.player_controls.initialize()

        self.messages['last_finished'] = await self.ctx.send(
            embed=self.get_finished_embed(),
            view=self.player_controls.get() if delete_after is None else None,
            delete_after=delete_after
        )

    def process_repeat(self) -> bool:
        is_last = self.track_list[self.current_queue] == len(self.queue) - 1

        if is_last and self.config['repeat'] == "off":
            return False

        if is_last and self.config['repeat'] == "all":
            self.track_list.append(0)
        elif self.config['repeat'] != "single":
            self.track_list.append(self.track_list[self.current_queue] + 1)

        self.current_queue += 1

        return True

    def process_shuffle(self) -> bool:
        if not self.config['shuffle']:
            return False

        choices = lambda: [x for x in range(0, len(self.queue)) if x not in self.shuffled_list]

        if len(self.queue) == 1:
            self.shuffled_list = []
        elif len(self.shuffled_list) == 0 or len(choices()) == 0:
            self.shuffled_list = [self.track_list[self.current_queue]]
            return self.process_shuffle()

        index = random.choice(choices())
        self.shuffled_list.append(index)
        self.track_list.append(index)
        self.current_queue += 1

        return True

    async def process_youtube(self, ctx: commands.Context, keyword: str):
        loading_msg = await ctx.send(embed=Embed("Loading..."))

        ytdl_list = await self.ytdl.extract_info(keyword)

        info = {}

        await self.bot.delete_message(loading_msg)

        if isinstance(ytdl_list, list):
            info = []
            for entry in ytdl_list:
                if entry['title'] != "[Deleted video]":
                    entry['url'] = f"https://www.youtube.com/watch?v={entry['id']}"
                    info.append(entry)

            await ctx.send(embed=Embed(f"Added {plural(len(ytdl_list), 'song', 'songs')} to queue."),
                                delete_after=5)
        elif ytdl_list:
            info = self.ytdl.parse_info(ytdl_list)
            await ctx.send(embed=Embed(
                title=f"Added song to queue #{len(self.queue) + 1}",
                description=info['title'],
            ), delete_after=5)
        else:
            await ctx.send(embed=Embed("Song failed to load."), delete_after=5)

        self.add_to_queue(info, requested=ctx.author)

    async def process_spotify(self, ctx: commands.Context, url: str) -> None:
        url = self.spotify.parse_url(url)
        ytdl = self.ytdl.create(self.bot, {"default_search": "ytsearch1"})

        if not url:
            await ctx.send(embed=Embed("Invalid spotify url."), delete_after=5)
            return

        processing_msg = None
        is_playlist = url['type'] == "playlist"
        playlist = []
        ytdl_list = []
        info = []
        error = 0

        if is_playlist:
            processing_msg = await ctx.send(embed=Embed("Converting to YouTube playlist. Please wait..."))
            playlist = await self.spotify.get_playlist(url['id'])
        else:
            processing_msg = await ctx.send(embed=Embed("Converting to YouTube track. Please wait..."))
            playlist.append(await self.spotify.get_track(url['id']))

        for item in playlist:
            track = item['track'] if is_playlist else item
            info = await ytdl.extract_info(f"{track['name']} {' '.join(artist['name'] for artist in track['artists'])}")

            if info is None:
                error += 1
                continue

            ytdl_list.append(info)

        await self.bot.delete_message(processing_msg)

        if len(ytdl_list) == 0:
            await ctx.send(embed=Embed("Failed to find similar song to YouTube."), delete_after=10)
            return

        if is_playlist:
            await ctx.send(embed=Embed(
                f"Added {plural(len(ytdl_list), 'song', 'songs')} to queue." + (" {error} failed to load." if error > 0 else "")
            ), delete_after=10)
        else:
            await ctx.send(embed=Embed(
                title=f"Added song to queue #{len(self.queue) + 1}",
                description=ytdl_list[0]['title'],
            ), delete_after=5)

        self.add_to_queue(ytdl_list, requested=ctx.author)

    async def process_search(self, ctx: commands.Context, keyword: str) -> None:
        msg = await ctx.send(embed=Embed("Searching..."))

        try:
            extracted = await self.ytdl.extract_info(keyword)
            ytdl_choices = self.ytdl.parse_choices(extracted)
        except YtdlError:
            await ctx.send(embed=Embed("No songs available."), delete_after=10)
            return

        await self.bot.delete_message(msg)

        choice = (await EmbedChoices(ctx, ytdl_choices).build()).value

        if choice < 0:
            return

        msg = await ctx.send(embed=Embed("Loading..."))

        info = await self.ytdl.process_entry(extracted[choice])
        info = self.ytdl.parse_info(info)

        await self.bot.delete_message(msg)

        await ctx.send(embed=Embed(
            title=f"You have selected #{choice + 1}. Adding song to queue #{len(self.queue) + 1}",
            description=info['title'],
        ), delete_after=5)

        self.add_to_queue(info, requested=ctx.author)

    @tasks.loop(count=1)
    async def reset_timeout(self) -> None:
        await asyncio.sleep(60 * 10)

        await self.bot.delete_message(self.messages['auto_paused'])
        await self.reset()

        msg = "Player has been reset due to timeout."
        log.cmd(self.ctx, msg)
        await self.ctx.send(embed=Embed(msg))

    async def on_member_leave(self):
        if self.connection and not self.connection.is_playing():
            return await self.reset()

        msg = "Player paused and will reset after 10 minutes if no one will listen :("
        log.cmd(self.ctx, msg, channel=self.last_voice_channel, user="N/A")
        self.messages['auto_paused'] = await self.ctx.send(embed=Embed(msg))
        if self.connection.is_playing():
            self.connection.pause()
        self.reset_timeout.start()

    async def on_member_join(self):
        if not self.reset_timeout.is_running():
            return

        await self.bot.delete_message(self.messages['auto_paused'])
        self.messages['auto_paused'] = None
        if self.connection.is_paused():
            self.connection.resume()
        self.reset_timeout.cancel()

    def add_to_queue(self, data: Union[List, dict], *, requested: discord.User = None) -> None:
        if not data:
            return

        if not isinstance(data, list):
            data = [data]

        for info in data:
            info['requested'] = requested or self.ctx.author
            self.queue.append(info)

    def update_config(self, key: str, value: Union[str, int]) -> None:
        self.db.set('music.' + key, value)
        self.db.save()

    def get_footer(self, now_playing):
        return [
            str(now_playing['requested']),
            format_seconds(now_playing['duration']) if now_playing['duration'] else "N/A",
            f"Volume: {self.config['volume']}%",
            f"Shuffle: {'on' if self.config['shuffle'] else 'off'}",
            f"Repeat: {self.config['repeat']}",
        ]

    def get_playing_embed(self):
        footer = [
            str(self.now_playing['requested']),
            format_seconds(self.now_playing['duration']) if self.now_playing['duration'] else "N/A",
            f"Volume: {self.config['volume']}%",
            f"Shuffle: {'on' if self.config['shuffle'] else 'off'}",
            f"Repeat: {self.config['repeat']}",
        ]

        embed = Embed(title=self.now_playing['title'], url=self.now_playing['url'])
        embed.set_author(
            name=f"Now Playing #{self.now_playing['index']}",
            icon_url="https://i.imgur.com/SBMH84I.png",
        )
        embed.set_footer(
            text=" | ".join(footer), icon_url=self.now_playing['requested'].display_avatar
        )

        return embed

    def get_finished_embed(self):
        footer = self.get_footer(self.previous_track)

        embed = Embed(title=self.previous_track['title'], url=self.previous_track['url'])
        embed.set_author(
            name=f"Finished Playing #{self.previous_track['index']}",
            icon_url="https://i.imgur.com/SBMH84I.png",
        )
        embed.set_footer(
            text=" | ".join(footer), icon_url=self.previous_track['requested'].display_avatar
        )

        return embed

    async def refresh_player_message(self, *, embed = False):
        self.player_controls.refresh()

        if self.messages['last_playing']:
            await self.messages['last_playing'].edit(
                embed=self.get_playing_embed() if embed else MISSING,
                view=self.player_controls.get()
            )
        elif self.messages['last_finished']:
            await self.messages['last_finished'].edit(
                embed=self.get_finished_embed() if embed else MISSING,
                view=self.player_controls.get()
            )

    async def clear_playing_messages(self):
        await self.bot.delete_message(
            self.messages['last_playing'],
            self.messages['last_finished'],
            self.messages['paused'],
            self.messages['resumed']
        )
        self.messages['last_playing'] = None
        self.messages['last_finished'] = None
