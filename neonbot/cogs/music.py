import re

from addict import Dict
from discord.ext import commands

from ..classes import YTDL, PaginationEmbed, Player
from ..helpers import log
from ..helpers.constants import CHOICES_EMOJI, FFMPEG_OPTIONS, YOUTUBE_REGEX
from ..helpers.date import format_seconds
from ..helpers.utils import Embed, check_args, embed_choices, plural

players = {}


def get_player(guild_id):
    if guild_id not in players.keys():
        players[guild_id] = Player(guild_id)

    return players[guild_id]


async def in_voice_channel(ctx):
    if ctx.author.voice != None and ctx.author.voice.channel != None:
        return True
    else:
        await ctx.send(embed=Embed("You need to be in a voice channel."))
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
                    args[1], {"server": get_player(ctx.guild.id), "bot": self.bot}
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
        player = get_player(ctx.guild.id)
        embed = info = loading_msg = None

        if keyword.isdigit():
            index = int(keyword)
            if index > len(player.queue) or index < 0:
                return await ctx.send(embed=Embed("Invalid index."), delete_after=5)
            await player.next(ctx, index=index - 1)
        elif re.search(YOUTUBE_REGEX, keyword):
            loading_msg = await ctx.send(embed=Embed("Loading..."))

            ytdl = await YTDL().extract_info(keyword)
            ytdl_list = ytdl.info

            if isinstance(ytdl_list, list):
                for entry in ytdl_list:
                    if entry.title == "[Deleted video]":
                        continue
                    entry.ytdl = ytdl
                    entry.url = f"https://www.youtube.com/watch?v={entry.id}"
                    player.add_to_queue(ctx, entry)

                embed = Embed(
                    f"Added {plural(len(ytdl_list), 'song', 'songs')} to queue."
                )
            elif ytdl_list:
                info = ytdl.get_info()
                embed = Embed(
                    title=f"Added song to queue #{len(player.queue)+1}",
                    description=info.title,
                )
            else:
                embed = Embed("Song failed to load.")
        else:
            msg = await ctx.send(embed=Embed("Searching..."))
            ytdl = await YTDL().extract_info(keyword)
            ytdl_choices = ytdl.get_choices()
            await msg.delete()
            if len(ytdl_choices) == 0:
                return await ctx.send(embed=Embed("No songs available."))
            choice = await embed_choices(ctx, ytdl_choices)
            if choice < 0:
                return
            await ytdl.process_entry(ytdl.info[choice])
            info = ytdl.get_info()
            if not info:
                return await ctx.send(
                    embed=Embed(
                        "Rate limited due to many song requests. Try again later."
                    ),
                    delete_after=10,
                )
            embed = Embed(
                title=f"You have selected #{choice+1}. Adding song to queue #{len(player.queue)+1}",
                description=info.title,
            )

        if info:
            player.add_to_queue(ctx, info)
        if loading_msg:
            await loading_msg.delete()
        if embed:
            await ctx.send(embed=embed, delete_after=5)

        if len(player.queue) > 0 and not ctx.voice_client:
            player.connection = await ctx.author.voice.channel.connect()
            log.cmd(ctx, f"Connected to {ctx.author.voice.channel}.")
            await player.play(ctx)

    @commands.command()
    async def pause(self, ctx):
        player = get_player(ctx.guild.id)

        if player.connection.is_paused():
            return

        player.connection.pause()
        log.cmd(ctx, "Player paused.")

        player.messages.paused = await ctx.send(
            embed=Embed(f"Player paused. `{ctx.prefix}resume` to resume.")
        )

    @commands.command()
    async def resume(self, ctx):
        player = get_player(ctx.guild.id)

        if player.connection.is_playing():
            return

        player.connection.resume()
        log.cmd(ctx, "Player resumed.")

        if player.messages.paused:
            await player.messages.paused.delete()

        await ctx.send(embed=Embed("Player resumed."), delete_after=5)

    @commands.command(aliases=["next"])
    async def skip(self, ctx):
        player = get_player(ctx.guild.id)
        player.connection.stop()

    @commands.command()
    async def stop(self, ctx):
        player = get_player(ctx.guild.id)
        await player.next(ctx, stop=True)
        player.current_queue = 0
        log.cmd(ctx, "Player stopped.")
        await ctx.send(embed=Embed("Player stopped."), delete_after=5)

    @commands.command()
    async def reset(self, ctx):
        player = get_player(ctx.guild.id)
        await player.next(ctx, stop=True)
        await player.connection.disconnect()
        del players[ctx.guild.id]
        await ctx.send(embed=Embed("Player reset."), delete_after=5)

    @commands.command()
    async def removesong(self, ctx, index: int):
        index -= 1
        player = get_player(ctx.guild.id)
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
            await player.next(ctx, index=player.current_queue)

    @commands.command(aliases=["vol"], usage="<1 - 100>")
    async def volume(self, ctx, vol: int = -1):
        player = get_player(ctx.guild.id)

        if vol == -1:
            return await ctx.send(
                embed=Embed(f"Volume is set to {player.config.volume}%."),
                delete_after=5,
            )
        elif vol < 1 or vol > 100:
            return await ctx.send(
                embed=Embed(f"Volume must be 1 - 100."), delete_after=5
            )

        player.connection.source.volume = vol / 100
        player.update_config("volume", vol)
        await ctx.send(embed=Embed(f"Volume changed to {vol}%"), delete_after=5)

    @commands.command(usage="<off | single | all>")
    async def repeat(self, ctx, args=None):
        player = get_player(ctx.guild.id)

        if args is None:
            return await ctx.send(
                embed=Embed(f"Repeat is set to {player.config.repeat}."), delete_after=5
            )
        if not await check_args(ctx, args, ["off", "single", "all"]):
            return

        player.update_config("repeat", args)
        await ctx.send(embed=Embed(f"Repeat changed to {args}."), delete_after=5)

    @commands.command()
    async def autoplay(self, ctx):
        player = get_player(ctx.guild.id)
        config = player.update_config("autoplay", not player.config.autoplay)
        await ctx.send(
            embed=Embed(
                f"Autoplay is set to {'enabled' if config.autoplay else 'disabled'}."
            ),
            delete_after=5,
        )

    @commands.command()
    async def shuffle(self, ctx):
        player = get_player(ctx.guild.id)
        config = player.update_config("shuffle", not player.config.shuffle)
        await ctx.send(
            embed=Embed(
                f"Shuffle is set to {'enabled' if config.shuffle else 'disabled'}."
            ),
            delete_after=5,
        )

    @commands.command(aliases=["np"])
    async def nowplaying(self, ctx):
        player = get_player(ctx.guild.id)
        config = player.config
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
    async def playlist(self, ctx):
        player = get_player(ctx.guild.id)
        config = player.config
        queue = player.queue
        queue_length = len(queue)
        embeds = []
        temp = []
        duration = 0

        if queue_length == 0:
            return await ctx.send(embed=Embed("Empty playlist."), delete_after=5)

        for i, song in enumerate(player.queue):
            description = f"`{'*' if player.current_queue == i else ''}{i+1}.` [{song.title}]({song.url})\n- - - `{format_seconds(song.duration) if song.duration else 'N/A'}` `{song.requested}`"
            temp.append(description)
            duration += song.duration or 0

            if (i != 0 and (i + 1) % 10 == 0) or i == len(queue) - 1:
                embeds.append(Embed("\n".join(temp)))
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


def setup(bot):
    bot.add_cog(Music(bot))
