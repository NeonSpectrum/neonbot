import logging
import re
from typing import Optional, cast

from nextcord.ext import commands

from ..classes.converters import Required
from ..classes.embed import Embed, PaginationEmbed
from ..classes.player import Player
from ..helpers.constants import SPOTIFY_REGEX, YOUTUBE_REGEX, ICONS
from ..helpers.date import format_seconds
from ..helpers.log import Log
from ..helpers.utils import plural

log = cast(Log, logging.getLogger(__name__))


def get_player(ctx: commands.Context) -> Player:
    players = ctx.bot.music
    if ctx.guild.id not in players.keys():
        players[ctx.guild.id] = Player(ctx)

    return players[ctx.guild.id]


async def in_voice(ctx: commands.Context) -> bool:
    if await ctx.bot.is_owner(ctx.author) and ctx.command.name == "reset":
        return True

    if not ctx.author.voice and ctx.invoked_with != "help":
        await ctx.send(embed=Embed("You need to be in the channel."), delete_after=5)
        return False
    return True


async def has_player(ctx: commands.Context) -> bool:
    player = get_player(ctx)

    if not player.connection and ctx.invoked_with != "help":
        await ctx.send(embed=Embed("No active player."), delete_after=5)
        return False
    return True


class Music(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.bot.load_music()

    @commands.command(aliases=["p"], usage="<url | keyword>")
    @commands.guild_only()
    @commands.check(in_voice)
    async def play(self, ctx: commands.Context, *, keyword: str = None) -> None:
        """Searches the url or the keyword and add it to queue."""

        player = get_player(ctx)
        player.ctx = ctx

        if keyword:
            if keyword.isdigit():
                index = int(keyword)
                if index > len(player.queue) or index < 0 or "removed" in player.queue[index - 1]:
                    await ctx.send(embed=Embed("Invalid index."), delete_after=5)
                    return

                if player.connection:
                    await player.next(index=index - 1)
                else:
                    player.track_list.append(index - 1)
                    player.current_queue = len(player.track_list) - 1
            elif re.search(YOUTUBE_REGEX, keyword):
                await player.process_youtube(ctx, keyword)
            elif re.search(SPOTIFY_REGEX, keyword):
                await player.process_spotify(ctx, keyword)
            elif keyword:
                await player.process_search(ctx, keyword)

        elif player.current_queue >= len(player.queue):
            player.current_queue = 0

        await player.connect()
        await player.play()

    @commands.command()
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def pause(self, ctx: commands.Context) -> None:
        """Pauses the current player."""

        player = get_player(ctx)
        await player.pause()

    @commands.command()
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def resume(self, ctx: commands.Context) -> None:
        """Resumes the current player."""

        player = get_player(ctx)
        await player.resume()

    @commands.command(aliases=["next"])
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def skip(self, ctx: commands.Context) -> None:
        """Skips the current song."""

        player = get_player(ctx)
        player.connection.stop()

    @commands.command()
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def stop(self, ctx: commands.Context) -> None:
        """Stops the current player and resets the track number to 1."""

        player = get_player(ctx)
        await player.stop()

        msg = "Player stopped."
        log.cmd(ctx, msg)
        await ctx.send(embed=Embed(msg), delete_after=5)

    @commands.command()
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def reset(self, ctx: commands.Context) -> None:
        """Resets the current player and disconnect to voice channel."""

        player = get_player(ctx)
        await player.reset()

        msg = "Player reset."
        log.cmd(ctx, msg)
        await ctx.send(embed=Embed(msg), delete_after=5)

    @commands.command()
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def removesong(self, ctx: commands.Context, index: int) -> None:
        """Remove the song with the index specified."""

        index -= 1
        player = get_player(ctx)

        try:
            queue = player.queue[index]
        except IndexError:
            await ctx.send(
                embed=Embed("There is no song in that index."), delete_after=5
            )
            return

        embed = Embed(title=queue['title'], url=queue['url'])
        embed.set_author(
            name=f"Removed song #{index + 1}", icon_url=ICONS['music']
        )
        embed.set_footer(text=queue['requested'], icon_url=queue['requested'].display_avatar)

        await ctx.send(embed=embed, delete_after=5)

        player.queue[index]['removed'] = True

        if index < player.current_queue:
            player.current_queue -= 1
        elif index == player.current_queue:
            if not player.queue:
                await player.next(stop=True)
            else:
                await player.next()

    @commands.command(aliases=["vol"], usage="<1 - 100>")
    @commands.guild_only()
    @commands.check(in_voice)
    async def volume(self, ctx: commands.Context, volume: Optional[int] = None) -> None:
        """Sets or gets player's volume."""

        player = get_player(ctx)

        if volume is None:
            await ctx.send(
                embed=Embed(f"Volume is set to {player.get_config('volume')}%."),
                delete_after=5,
            )
            return
        elif volume < 1 or volume > 100:
            await ctx.send(
                embed=Embed("Volume must be 1 - 100."), delete_after=5
            )
            return

        await player.volume(volume)
        await ctx.send(embed=Embed(f"Volume changed to {volume}%"), delete_after=5)

    @commands.command(usage="<off | single | all>")
    @commands.guild_only()
    @commands.check(in_voice)
    async def repeat(
        self,
        ctx: commands.Context,
        mode: Required("off", "single", "all") = None,  # type:ignore
    ) -> None:
        """Sets or gets player's repeat mode."""

        player = get_player(ctx)

        if mode is None:
            await ctx.send(
                embed=Embed(f"Repeat is set to {player.get_config('repeat')}."), delete_after=5
            )
            return

        await player.repeat(mode)

    @commands.command()
    @commands.guild_only()
    @commands.check(in_voice)
    async def shuffle(self, ctx: commands.Context) -> None:
        """Enables/disables player's shuffle mode."""

        player = get_player(ctx)
        await player.shuffle()

    @commands.command(aliases=["np"])
    @commands.guild_only()
    @commands.check(has_player)
    @commands.check(in_voice)
    async def nowplaying(self, ctx: commands.Context) -> None:
        """Displays in brief description of the current playing."""

        player = get_player(ctx)

        if not player.connection.is_playing():
            await ctx.send(embed=Embed("No song playing."), delete_after=5)
            return

        now_playing = player.now_playing

        footer = player.get_footer(now_playing)
        footer.pop(1)

        embed = Embed()
        embed.add_field("Uploader", now_playing['uploader'])
        embed.add_field("Upload Date", now_playing['upload_date'])
        embed.add_field("Duration", now_playing['formatted_duration'])
        embed.add_field("Views", now_playing['view_count'])
        embed.add_field("Description", now_playing['description'], inline=False)
        embed.set_author(
            name=now_playing['title'],
            url=now_playing['url'],
            icon_url=ICONS['music'],
        )
        embed.set_thumbnail(url=now_playing['thumbnail'])
        embed.set_footer(
            text=" | ".join(footer), icon_url=now_playing['requested'].display_avatar
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["list"])
    @commands.guild_only()
    @commands.check(in_voice)
    async def playlist(self, ctx: commands.Context) -> None:
        """List down all songs in the player's queue."""

        player = get_player(ctx)
        queue = player.queue
        embeds = []
        duration = 0

        if not queue:
            await ctx.send(embed=Embed("Empty playlist."), delete_after=5)
            return

        for i in range(0, len(player.queue), 10):
            temp = []
            for index, song in enumerate(player.queue[i: i + 10], i):
                is_current = player.track_list[player.current_queue] == index
                title = f"`{'*' if is_current else ''}{index + 1}.` [{song['title']}]({song['url']})"
                description = f"""\
{f"~~{title}~~" if "removed" in song else title}
- - - `{format_seconds(song.get('duration')) if song.get('duration') else "N/A"}` `{song['requested']}`"""

                duration += song.get('duration') or 0

                temp.append(description)
            embeds.append(Embed("\n".join(temp)))

        footer = [
            f"{plural(len(queue), 'song', 'songs')}",
            format_seconds(duration),
            f"Volume: {player.get_config('volume')}%",
            f"Shuffle: {'on' if player.get_config('shuffle') else 'off'}",
            f"Repeat: {player.get_config('repeat')}",
        ]

        pagination = PaginationEmbed(ctx, embeds=embeds)
        pagination.embed.set_author(
            name="Player Queue", icon_url=ICONS['music']
        )
        pagination.embed.set_footer(
            text=" | ".join(footer), icon_url=self.bot.user.display_avatar
        )
        await pagination.build()

    @commands.command(aliases=["pp"])
    @commands.guild_only()
    @commands.check(in_voice)
    async def playplaylist(self, ctx: commands.Context, *, name: str):
        """Play playlist on saved playlist."""

        player = get_player(ctx)
        player.ctx = ctx

        playlist = player.get_config('playlist.' + name)

        if not playlist:
            await ctx.send(embed=Embed('Playlist not found.'), delete_after=5)
            return

        if len(playlist.get('tracks') or []) == 0:
            await ctx.send(embed=Embed('Empty playlist.'), delete_after=5)
            return

        await player.process_playlist(ctx, playlist['tracks'])
        await player.connect()
        await player.play()

    @commands.command(aliases=["sp"])
    @commands.guild_only()
    @commands.check(in_voice)
    async def saveplaylist(self, ctx: commands.Context, *, name: str):
        """Save current playlist to saved playlist."""

        player = get_player(ctx)

        playlist = player.get_config('playlist.' + name)

        if playlist and playlist.get('owner') != ctx.author.id:
            await ctx.send(embed=Embed(f"You are not the owner of the playlist. You can't modify it."))
            return

        await player.update_config('playlist', {
            name: {
                "tracks": [queue['id'] for queue in player.queue],
                "owner": ctx.author.id
            }
        })

        await ctx.send(embed=Embed(f"Playlist added! Type `{ctx.prefix}pp {name}` to play it."), delete_after=5)

    @commands.command(aliases=["dp"])
    @commands.guild_only()
    @commands.check(in_voice)
    async def deleteplaylist(self, ctx: commands.Context, *, name: str):
        """Delete playlist on saved playlist."""

        player = get_player(ctx)

        playlist = player.get_config('playlist.' + name)

        if not playlist:
            await ctx.send(embed=Embed('Playlist not found.'), delete_after=5)
            return

        if playlist.get('owner') != ctx.author.id:
            await ctx.send(embed=Embed(f"You are not the owner of the playlist. You can't delete it."))
            return

        player.get_config('playlist').pop(name)
        await player.db.save()

        await ctx.send(embed=Embed(f"Playlist deleted!"), delete_after=5)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Music(bot))
