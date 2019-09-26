import logging
import re
import textwrap
from typing import List, Optional, cast

import discord
from discord.ext import commands

from .. import bot
from .. import music as players
from ..classes import PaginationEmbed, Player
from ..helpers.constants import SPOTIFY_REGEX, YOUTUBE_REGEX
from ..helpers.date import format_seconds
from ..helpers.log import Log
from ..helpers.utils import Embed, check_args, plural

log = cast(Log, logging.getLogger(__name__))


def get_player(guild: discord.Guild) -> Player:
    if guild.id not in players.keys():
        players[guild.id] = Player(guild)

    return players[guild.id]


async def in_voice(ctx: commands.Context) -> bool:
    if await ctx.bot.is_owner(ctx.author) and ctx.command.name == "reset":
        return True

    if not ctx.author.voice and ctx.invoked_with != "help":
        await ctx.send(embed=Embed("You need to be in the channel."), delete_after=5)
        return False
    return True


async def has_player(ctx: commands.Context) -> bool:
    player = get_player(ctx.guild)

    if not player.connection and ctx.invoked_with != "help":
        await ctx.send(embed=Embed("No active player."), delete_after=5)
        return False
    return True


class Music(commands.Cog):
    def __init__(self) -> None:
        bot.load_music()

    @commands.command(aliases=["p"], usage="<url | keyword>")
    @commands.guild_only()
    @commands.check(in_voice)
    async def play(self, ctx: commands.Context, *, keyword: str = None) -> None:
        """Searches the url or the keyword and add it to queue."""

        player = get_player(ctx.guild)
        embed = info = loading_msg = None

        if keyword:
            if keyword.isdigit():
                index = int(keyword)
                if index > len(player.queue) or index < 0:
                    return await ctx.send(embed=Embed("Invalid index."), delete_after=5)
                if player.connection:
                    await player.next(ctx, index=index - 1)
                else:
                    player.current_queue = index - 1
            elif re.search(YOUTUBE_REGEX, keyword):
                info, embed = await player.process_youtube(ctx, keyword)
            elif re.search(SPOTIFY_REGEX, keyword):
                info, embed = await player.process_spotify(ctx, keyword)
            elif keyword:
                info, embed = await player.process_search(ctx, keyword)
                if not info:
                    return

        if info:
            player.add_to_queue(info, ctx.author)
        if loading_msg:
            await loading_msg.delete()
        if embed:
            await ctx.send(embed=embed, delete_after=5)

        if any(player.queue) and not ctx.voice_client:
            player.connection = await ctx.author.voice.channel.connect()
            log.cmd(ctx, f"Connected to {ctx.author.voice.channel}.")
        if player.connection and not player.connection.is_playing():
            await player.play(ctx)

    @commands.command()
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def pause(self, ctx: commands.Context) -> None:
        """Pauses the current player."""

        player = get_player(ctx.guild)

        if player.connection.is_paused():
            return

        player.connection.pause()
        log.cmd(ctx, "Player paused.")

        player.messages.paused = await ctx.send(
            embed=Embed(f"Player paused. `{ctx.prefix}resume` to resume.")
        )

    @commands.command()
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def resume(self, ctx: commands.Context) -> None:
        """Resumes the current player."""

        player = get_player(ctx.guild)

        if player.connection.is_playing():
            return

        player.connection.resume()
        log.cmd(ctx, "Player resumed.")

        if player.messages.paused:
            await player.messages.paused.delete()

        await ctx.send(embed=Embed("Player resumed."), delete_after=5)

    @commands.command(aliases=["next"])
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def skip(self, ctx: commands.Context) -> None:
        """Skips the current song."""

        player = get_player(ctx.guild)
        player.connection.stop()

    @commands.command()
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def stop(self, ctx: commands.Context) -> None:
        """Stops the current player and resets the track number to 1."""

        player = get_player(ctx.guild)
        await player.next(ctx, stop=True)
        player.current_queue = 0
        log.cmd(ctx, "Player stopped.")
        await ctx.send(embed=Embed("Player stopped."), delete_after=5)

    @commands.command()
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def reset(self, ctx: commands.Context) -> None:
        """Resets the current player and disconnect to voice channel."""

        player = get_player(ctx.guild)
        await player.next(ctx, stop=True)
        await player.connection.disconnect()
        del players[ctx.guild.id]
        await ctx.send(embed=Embed("Player reset."), delete_after=5)

    @commands.command()
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def removesong(self, ctx: commands.Context, index: int) -> None:
        """Remove the song with the index specified."""

        index -= 1
        player = get_player(ctx.guild)
        queue = player.queue[index]

        if not queue:
            await ctx.send(
                embed=Embed("There is no song in that index."), delete_after=5
            )

        embed = Embed(title=queue.title, url=queue.url)
        embed.set_author(
            name=f"Removed song #{index+1}", icon_url="https://i.imgur.com/SBMH84I.png"
        )
        embed.set_footer(text=queue.requested, icon_url=queue.requested.avatar_url)

        await ctx.send(embed=embed, delete_after=5)

        del player.queue[index]

        if index < player.current_queue:
            player.current_queue -= 1
        elif index == player.current_queue:
            if not player.queue:
                await player.next(ctx, stop=True)
            else:
                await player.next(ctx, index=player.current_queue)

    @commands.command(aliases=["vol"], usage="<1 - 100>")
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def volume(self, ctx: commands.Context, volume: Optional[int] = None) -> None:
        """Sets or gets player's volume."""

        player = get_player(ctx.guild)

        if volume is None:
            return await ctx.send(
                embed=Embed(f"Volume is set to {player.config.volume}%."),
                delete_after=5,
            )
        elif volume < 1 or volume > 100:
            return await ctx.send(
                embed=Embed(f"Volume must be 1 - 100."), delete_after=5
            )

        player.connection.source.volume = volume / 100
        player.update_config("volume", volume)
        await ctx.send(embed=Embed(f"Volume changed to {volume}%"), delete_after=5)

    @commands.command(usage="<off | single | all>")
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def repeat(self, ctx: commands.Context, mode: Optional[str] = None) -> None:
        """Sets or gets player's repeat mode."""

        player = get_player(ctx.guild)

        if mode is None:
            return await ctx.send(
                embed=Embed(f"Repeat is set to {player.config.repeat}."), delete_after=5
            )
        if not await check_args(ctx, mode, ["off", "single", "all"]):
            return

        player.update_config("repeat", mode)
        await ctx.send(embed=Embed(f"Repeat changed to {mode}."), delete_after=5)

    @commands.command()
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def autoplay(self, ctx: commands.Context) -> None:
        """Enables/disables player's autoplay mode."""

        player = get_player(ctx.guild)
        config = player.update_config("autoplay", not player.config.autoplay)
        await ctx.send(
            embed=Embed(
                f"Autoplay is set to {'enabled' if config.autoplay else 'disabled'}."
            ),
            delete_after=5,
        )

    @commands.command()
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def shuffle(self, ctx: commands.Context) -> None:
        """Enables/disables player's shuffle mode."""

        player = get_player(ctx.guild)
        config = player.update_config("shuffle", not player.config.shuffle)
        await ctx.send(
            embed=Embed(
                f"Shuffle is set to {'enabled' if config.shuffle else 'disabled'}."
            ),
            delete_after=5,
        )

    @commands.command(aliases=["np"])
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def nowplaying(self, ctx: commands.Context) -> None:
        """Displays in brief description of the current playing."""

        player = get_player(ctx.guild)
        config = player.config

        if not player.connection.is_playing():
            return await ctx.send(embed=Embed("No song playing."), delete_after=5)

        now_playing = player.now_playing

        footer = [
            str(now_playing.requested),
            f"Volume: {config.volume}%",
            f"Repeat: {config.repeat}",
            f"Shuffle: {'on' if config.shuffle else 'off'}",
            f"Autoplay: {'on' if config.autoplay else 'off'}",
        ]

        embed = Embed()
        embed.add_field(name="Uploader", value=now_playing.uploader)
        embed.add_field(name="Upload Date", value=now_playing.upload_date)
        embed.add_field(name="Duration", value=format_seconds(now_playing.duration))
        embed.add_field(name="Views", value=now_playing.view_count)
        embed.add_field(name="Description", value=now_playing.description, inline=False)
        embed.set_author(
            name=now_playing.title,
            url=now_playing.url,
            icon_url="https://i.imgur.com/mG8QKe7.png",
        )
        embed.set_thumbnail(url=now_playing.thumbnail)
        embed.set_footer(
            text=" | ".join(footer), icon_url=now_playing.requested.avatar_url
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["list"])
    @commands.guild_only()
    @commands.check(in_voice)
    async def playlist(self, ctx: commands.Context) -> None:
        """List down all songs in the player's queue."""

        player = get_player(ctx.guild)
        config = player.config
        queue = player.queue
        embeds = []
        temp: List[str] = []
        duration = 0

        if not queue:
            return await ctx.send(embed=Embed("Empty playlist."), delete_after=5)

        for i in range(0, len(player.queue), 10):
            temp = []
            for index, song in enumerate(player.queue[i : i + 10], i):
                description = textwrap.dedent(
                    f"""\
                `{'*' if player.current_queue == index else ''}{index+1}.` [{song.title}]({song.url})
                - - - `{format_seconds(song.duration) if song.duration else 'N/A'}` `{song.requested}`"""
                )
                temp.append(description)
                duration += song.duration or 0
            embeds.append(Embed("\n".join(temp)))

        footer = [
            f"{plural(len(queue), 'song', 'songs')}",
            format_seconds(duration),
            f"Volume: {config.volume}%",
            f"Repeat: {config.repeat}",
            f"Shuffle: {'on' if config.shuffle else 'off'}",
            f"Autoplay: {'on' if config.autoplay else 'off'}",
        ]

        pagination = PaginationEmbed(ctx, embeds=embeds)
        pagination.embed.set_author(
            name="Player Queue", icon_url="https://i.imgur.com/SBMH84I.png"
        )
        pagination.embed.set_footer(
            text=" | ".join(footer), icon_url=bot.user.avatar_url
        )
        await pagination.build()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Music())
