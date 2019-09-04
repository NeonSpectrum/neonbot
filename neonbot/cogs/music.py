import asyncio
import random
import re
from copy import deepcopy
from threading import Thread

import discord
import youtube_dl
from addict import Dict
from discord.ext import commands

from helpers import log
from helpers.constants import CHOICES_EMOJI, FFMPEG_OPTIONS, YOUTUBE_REGEX
from helpers.database import Database
from helpers.utils import (
    Embed,
    PaginationEmbed,
    check_args,
    embed_choices,
    format_seconds,
    plural,
)
from helpers.ytdl import YTDL, get_related_videos, is_link_expired

servers = Dict()

DEFAULT_CONFIG = Dict(
    {
        "connection": None,
        "config": None,
        "current_queue": 0,
        "queue": [],
        "shuffled_list": [],
        "tasks": [],
        "disable_after": False,
        "messages": {"last_playing": None, "last_finished": None, "paused": None},
    }
)


def get_server(guild_id):
    if guild_id not in servers.keys():
        config = Database(guild_id).config
        servers[guild_id] = deepcopy(DEFAULT_CONFIG)
        servers[guild_id].config = config.music

    return servers[guild_id]


def update_config(guild_id, key, value):
    database = Database(guild_id)
    database.config.music[key] = value
    database.update_config().refresh_config()
    servers[guild_id].config = database.config.music
    return servers[guild_id].config


async def in_voice_channel(ctx):
    if ctx.author.voice != None and ctx.author.voice.channel != None:
        return True
    else:
        await ctx.send(embed=Embed(description="You need to be in a voice channel."))
        return False


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def evalmusic(self, ctx, *args):
        try:
            if args[0] == "await":
                output = await eval(
                    args[1], {"server": get_server(ctx.guild.id), "bot": self.bot}
                )
            else:
                output = eval(args[0])
        except Exception as e:
            output = e
        finally:
            output = str(output)

        max_length = 1800

        if len(output) > max_length:
            msg_array = [
                output[i : i + max_length] for i in range(0, len(output), max_length)
            ]
        else:
            msg_array = [output]

        for i in msg_array:
            await ctx.send(f"```py\n{i}```")

    @commands.command(aliases=["p"], usage="<url | keyword>")
    @commands.check(in_voice_channel)
    async def play(self, ctx, *, keyword=None):
        server = get_server(ctx.guild.id)
        embed = info = loading_msg = None

        if keyword.isdigit():
            index = int(keyword)
            if index > len(server.queue) or index < 0:
                return await ctx.send(
                    embed=Embed(description="Invalid index.", delete_after=5)
                )
            await self._next(ctx, index=index - 1)
        elif re.search(YOUTUBE_REGEX, keyword):
            loading_msg = await ctx.send(embed=Embed(description="Loading..."))

            ytdl = await YTDL().extract_info(keyword)
            ytdl_list = ytdl.info

            if isinstance(ytdl_list, list):
                for entry in ytdl_list:
                    entry.ytdl = ytdl
                    entry.url = f"https://www.youtube.com/watch?v={entry.id}"
                    self._add_to_queue(ctx, entry)
                    print(entry)
                    
                embed = Embed(
                    description=f"Added {plural(len(ytdl_list), 'song', 'songs')} to queue."
                )
            elif ytdl_list:
                info = ytdl.get_info()
                embed = Embed(
                    title=f"Added song to queue #{len(server.queue)+1}",
                    description=info.title,
                )
            else:
                embed = Embed(description="Song failed to load.")
        else:
            msg = await ctx.send(embed=Embed(description="Searching..."))
            ytdl = await YTDL().extract_info(keyword)
            ytdl_choices = ytdl.get_choices()
            await msg.delete()
            if len(ytdl_choices) == 0:
                return await ctx.send(embed=Embed(description="No songs available."))
            choice = await embed_choices(ctx, ytdl_choices)
            if choice < 0:
                return
            await ytdl.process_entry(ytdl.info[choice])
            info = ytdl.get_info()
            if not info:
                return await ctx.send(embed=Embed(description="Rate limited due to many song requests. Try again later."), delete_after=10)
            embed = Embed(
                title=f"You have selected #{choice+1}. Adding song to queue #{len(server.queue)+1}",
                description=info.title,
            )
            
        if info:
            self._add_to_queue(ctx, info)
        if loading_msg:
            await loading_msg.delete()
        if embed:
            await ctx.send(embed=embed, delete_after=5)
            
        if len(server.queue) > 0 and not ctx.voice_client:
            await self._connect(ctx)
            await self._play(ctx)

    @commands.command()
    async def pause(self, ctx):
        server = get_server(ctx.guild.id)

        if server.connection.is_paused():
            return

        server.connection.pause()
        log.cmd(ctx, "Player paused.")

        server.messages.paused = await ctx.send(
            embed=Embed(description=f"Player paused. `{ctx.prefix}resume` to resume.")
        )

    @commands.command()
    async def resume(self, ctx):
        server = get_server(ctx.guild.id)

        if server.connection.is_playing():
            return

        server.connection.resume()
        log.cmd(ctx, "Player resumed.")

        if server.messages.paused:
            await server.messages.paused.delete()

        await ctx.send(embed=Embed(description="Player resumed.", delete_after=5))

    @commands.command(aliases=["next"])
    async def skip(self, ctx):
        server = get_server(ctx.guild.id)
        server.connection.stop()

    @commands.command()
    async def stop(self, ctx):
        server = get_server(ctx.guild.id)
        await self._next(ctx, stop=True)
        server.current_queue = 0
        log.cmd(ctx, "Player stopped.")
        await ctx.send(embed=Embed(description="Player stopped.", delete_after=5))

    @commands.command()
    async def reset(self, ctx):
        server = get_server(ctx.guild.id)
        await self._next(ctx, stop=True)
        await server.connection.disconnect()
        [task.cancel() for task in server.tasks]
        del servers[ctx.guild.id]
        await ctx.send(embed=Embed(description="Player reset.", delete_after=5))

    @commands.command()
    async def removesong(self, ctx, index: int):
        index -= 1
        server = get_server(ctx.guild.id)
        queue = server.queue[index]

        if not queue:
            await ctx.send(
                embed=Embed(description="There is no song in that index."),
                delete_after=5,
            )

        embed = Embed(title=queue.title, url=queue.url)
        embed.set_author(
            name=f"Removed song #{index+1}", icon_url="https://i.imgur.com/SBMH84I.png"
        )
        embed.set_footer(text=queue.requested, icon_url=queue.requested.avatar_url)

        await ctx.send(embed=embed, delete_after=5)

        del server.queue[index]

        if index < server.current_queue:
            server.current_queue -= 1
        elif index == server.current_queue:
            await self._next(ctx, index=server.current_queue)

    @commands.command(aliases=["vol"], usage="<1 - 100>")
    async def volume(self, ctx, vol: int = -1):
        server = get_server(ctx.guild.id)

        if vol == -1:
            return await ctx.send(
                embed=Embed(description=f"Volume is set to {server.config.volume}%."),
                delete_after=5,
            )
        elif vol < 1 or vol > 100:
            return await ctx.send(
                embed=Embed(description=f"Volume must be 1 - 100."), delete_after=5
            )

        server.connection.source.volume = vol / 100
        update_config(ctx.guild.id, "volume", vol)
        await ctx.send(
            embed=Embed(description=f"Volume changed to {vol}%", delete_after=5)
        )

    @commands.command(usage="<off | single | all>")
    async def repeat(self, ctx, args=None):
        server = get_server(ctx.guild.id)

        if args is None:
            return await ctx.send(
                embed=Embed(description=f"Repeat is set to {server.config.repeat}."),
                delete_after=5,
            )
        if not await check_args(ctx, args, ["off", "single", "all"]):
            return

        update_config(ctx.guild.id, "repeat", args)
        await ctx.send(
            embed=Embed(description=f"Repeat changed to {args}.", delete_after=5)
        )

    @commands.command()
    async def autoplay(self, ctx):
        server = get_server(ctx.guild.id)
        config = update_config(ctx.guild.id, "autoplay", not server.config.autoplay)
        await ctx.send(
            embed=Embed(
                description=f"Autoplay is set to {'enabled' if config.autoplay else 'disabled'}."
            ),
            delete_after=5,
        )

    @commands.command()
    async def shuffle(self, ctx):
        server = get_server(ctx.guild.id)
        config = update_config(ctx.guild.id, "shuffle", not server.config.shuffle)
        await ctx.send(
            embed=Embed(
                description=f"Shuffle is set to {'enabled' if config.shuffle else 'disabled'}."
            ),
            delete_after=5,
        )

    @commands.command(aliases=["np"])
    async def nowplaying(self, ctx):
        server = get_server(ctx.guild.id)
        config = server.config
        current_queue = self._get_current_queue(server)

        footer = [
            str(current_queue.requested),
            f"Volume: {config.volume}%",
            f"Repeat: {config.repeat}",
            f"Shuffle: {'on' if config.shuffle else 'off'}",
            f"Autoplay: {'on' if config.autoplay else 'off'}",
        ]

        embed = Embed()
        embed.add_field(name="Uploader", value=current_queue.uploader)
        embed.add_field(name="Upload Date", value=current_queue.upload_date)
        embed.add_field(name="Duration", value=format_seconds(current_queue.duration))
        embed.add_field(name="Views", value=current_queue.view_count)
        embed.add_field(
            name="Description", value=current_queue.description, inline=False
        )
        embed.set_author(
            name=current_queue.title,
            url=current_queue.url,
            icon_url="https://i.imgur.com/mG8QKe7.png",
        )
        embed.set_thumbnail(url=current_queue.thumbnail)
        embed.set_footer(
            text=" | ".join(footer), icon_url=current_queue.requested.avatar_url
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["list"])
    async def playlist(self, ctx):
        server = get_server(ctx.guild.id)
        config = server.config
        queue = server.queue
        queue_length = len(queue)
        embeds = []
        temp = []
        duration = 0

        if queue_length == 0:
            return await ctx.send(
                embed=Embed(description="Empty playlist.", delete_after=5)
            )

        for i, song in enumerate(server.queue):
            description = f"`{'*' if server.current_queue == i else ''}{i+1}.` [{song.title}]({song.url})\n- - - `{format_seconds(song.duration) if song.duration else 'N/A'}` `{song.requested}`"
            temp.append(description)
            duration += song.duration or 0

            if (i != 0 and (i + 1) % 10 == 0) or i == len(queue) - 1:
                embeds.append(Embed(description="\n".join(temp)))
                temp = []

        footer = [
            f"{plural(queue_length, 'song', 'songs')}",
            format_seconds(duration),
            f"Volume: {config.volume}%",
            f"Repeat: {config.repeat}",
            f"Shuffle: {'on' if config.shuffle else 'off'}",
            f"Autoplay: {'on' if config.autoplay else 'off'}",
        ]

        embed = PaginationEmbed(array=embeds, authorized_users=[ctx.author.id])
        embed.set_author(
            name="Player Queue", icon_url="https://i.imgur.com/SBMH84I.png"
        )
        embed.set_footer(text=" | ".join(footer), icon_url=self.bot.user.avatar_url)
        await embed.build(ctx)

    async def _play(self, ctx):
        server = get_server(ctx.guild.id)
        current_queue = self._get_current_queue(server)

        if not current_queue.stream and current_queue.ytdl:
            await current_queue.ytdl.process_entry(current_queue)
            info = current_queue.ytdl.get_info()
            info.requested = current_queue.requested
            server.queue[server.current_queue] = current_queue = info
        
        if is_link_expired(current_queue.stream):
            log.info("Link expired:", current_queue.title)
            ytdl = await YTDL().extract_info(current_queue.id)
            current_queue = ytdl.get_info()
            log.info("Fetched new link for", current_queue.title)

        try:
            song = discord.FFmpegPCMAudio(
                current_queue.stream, before_options=FFMPEG_OPTIONS
            )
            source = discord.PCMVolumeTransformer(
                song, volume=server.config.volume / 100
            )
        except discord.ClientException as e:
            log.warn(e)
            return await ctx.send("Error while playing the song.")

        async def after(error):
            if error:
                log.warn("After play error:", error)
            if not server.disable_after:
                await self._next(ctx)

        server.connection.play(
            source, after=lambda error: self.bot.loop.create_task(after(error))
        )
        await self._playing_message(ctx)
        server.disable_after = False

    async def _next(self, ctx, *, index=None, stop=False):
        server = get_server(ctx.guild.id)
        config = server.config

        await self._finished_message(ctx, delete_after=5 if stop else None)

        if stop or index is not None:
            server.disable_after = True
            server.connection.stop()

            if stop:
                return

            if (
                len(server.queue) == index
                and server.current_queue == len(server.queue) - 1
            ):
                if config.repeat == "off" and config.autoplay:
                    await self._process_autoplay(ctx)
                    server.current_queue += 1
                else:
                    server.current_queue = 0
            else:
                server.current_queue = index
            return await self._play(ctx)

        if config.shuffle or await self._process_repeat(ctx):
            if config.shuffle:
                server.current_queue = self._process_shuffle(ctx)
            await self._play(ctx)

    async def _playing_message(self, ctx, index=None, delete_after=None):
        server = get_server(ctx.guild.id)
        config = server.config
        index = index if index != None else server.current_queue
        current_queue = server.queue[index]

        log.cmd(ctx, f"Now playing {current_queue.title}", user=current_queue.requested)

        if server.messages.last_playing:
            await server.messages.last_playing.delete()

        footer = [
            str(current_queue.requested),
            format_seconds(current_queue.duration) if current_queue.duration else "N/A",
            f"Volume: {config.volume}%",
            f"Repeat: {config.repeat}",
            f"Shuffle: {'on' if config.shuffle else 'off'}",
            f"Autoplay: {'on' if config.autoplay else  'off'}",
        ]

        embed = Embed(title=current_queue.title, url=current_queue.url)
        embed.set_author(
            name=f"Now Playing #{index+1}", icon_url="https://i.imgur.com/SBMH84I.png"
        )
        embed.set_footer(
            text=" | ".join(footer), icon_url=current_queue.requested.avatar_url
        )

        server.messages.last_playing = await ctx.send(
            embed=embed, delete_after=delete_after
        )

    async def _finished_message(self, ctx, index=None, delete_after=None):
        server = get_server(ctx.guild.id)
        config = server.config
        index = index if index != None else server.current_queue
        current_queue = server.queue[index]

        log.cmd(
            ctx, f"Finished playing {current_queue.title}", user=current_queue.requested
        )

        if server.messages.last_finished:
            await server.messages.last_finished.delete()

        footer = [
            str(current_queue.requested),
            format_seconds(current_queue.duration) if current_queue.duration else "N/A",
            f"Volume: {config.volume}%",
            f"Repeat: {config.repeat}",
            f"Shuffle: {'on' if config.shuffle else 'off'}",
            f"Autoplay: {'on' if config.autoplay else  'off'}",
        ]

        embed = Embed(title=current_queue.title, url=current_queue.url)
        embed.set_author(
            name=f"Finished Playing #{index+1}",
            icon_url="https://i.imgur.com/SBMH84I.png",
        )
        embed.set_footer(
            text=" | ".join(footer), icon_url=current_queue.requested.avatar_url
        )

        server.messages.last_finished = await ctx.send(
            embed=embed, delete_after=delete_after
        )

    async def _process_repeat(self, ctx):
        server = get_server(ctx.guild.id)
        config = server.config

        if server.current_queue == len(server.queue) - 1:
            if config.repeat == "all":
                server.current_queue = 0
            elif config.repeat == "off":
                if config.autoplay:
                    await self._process_autoplay(ctx)
                    server.current_queue += 1
                else:
                    # reset queue to index 0 and stop playing
                    server.current_queue = 0
                    return False
        elif config.repeat != "single":
            server.current_queue += 1

        return True

    def _process_shuffle(self, ctx):
        server = get_server(ctx.guild.id)

        if server.current_queue in server.shuffled_list:
            server.shuffled_list.append(server.current_queue)
        if len(server.shuffled_list) == len(server.queue):
            server.shuffled_list = [server.current_queue]
        while True:
            index = random.randint(0, len(server.queue) - 1)
            if index not in server.shuffled_list:
                return index

    async def _process_autoplay(self, ctx):
        server = get_server(ctx.guild.id)
        current_queue = self._get_current_queue(server)

        related_videos = await get_related_videos(current_queue.id)
        filtered_videos = []

        for video in related_videos:
            existing = (
                len([queue for queue in server.queue if queue.id == video.id.videoId])
                > 0
            )
            if not existing:
                filtered_videos.append(video)

        video_id = filtered_videos[0].id.videoId

        ytdl = await YTDL().extract_info(video_id)
        info = ytdl.get_info()
        self._add_to_queue(ctx, info, requested=ctx.author)

    async def _connect(self, ctx):
        server = get_server(ctx.guild.id)
        if not ctx.voice_client:
            server.connection = await ctx.author.voice.channel.connect()
            log.cmd(ctx, f"Connected to {ctx.author.voice.channel}.")

    def _add_to_queue(self, ctx, data, requested=None):
        server = get_server(ctx.guild.id)
        data.requested = requested or ctx.author
        server.queue.append(data)

    def _get_current_queue(self, server):
        return server.queue[server.current_queue]


def setup(bot):
    bot.add_cog(Music(bot))
