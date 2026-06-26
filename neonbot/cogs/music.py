from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from i18n import t

from neonbot import NeonBot
from neonbot.discord_ui.decorators import has_permission, in_voice, has_player
from neonbot.discord_ui.embed import Embed, PaginationEmbed
from neonbot.music.enums import Repeat
from neonbot.utils import log
from neonbot.utils.constants import ICONS
from neonbot.utils.functions import format_milliseconds

if TYPE_CHECKING:
    from neonbot.music.player import Player


class Music(commands.Cog):
    def __init__(self, bot: 'NeonBot'):
        self.bot = bot

    @commands.hybrid_command(name='play', aliases=['p'], )
    @app_commands.describe(query='Enter keyword or url...')
    @has_permission()
    @in_voice()
    @commands.guild_only()
    async def play(self, ctx: commands.Context['NeonBot'], *, query: str) -> None:
        """Searches the url or the keyword and add it to queue. This will queue the first search."""

        player: Player = await self.bot.create_player_instance(ctx.guild.id, ctx=ctx)

        # Clear autoplay list whenever there's new song
        player.autoplay_list = []

        await player.search(query)

        if len(player.track_list) == 0:
            return

        await player.connect()

        if not player.is_playing:
            await player.play_next()

    @commands.hybrid_command(name='playrandom', aliases=['pr'], )
    @has_permission()
    @in_voice()
    @commands.guild_only()
    async def playrandom(self, ctx: commands.Context['NeonBot']):
        player: Player = await self.bot.create_player_instance(ctx.guild.id, ctx=ctx)

        await player.search_random()

        if len(player.track_list) == 0:
            return

        await player.connect()

        if not player.is_playing:
            await player.play_next()

    @commands.hybrid_command(name='nowplaying', aliases=['np'])
    @has_permission()
    @in_voice()
    @has_player()
    @commands.guild_only()
    async def nowplaying(self, ctx: commands.Context['NeonBot']) -> None:
        """Displays in brief description of the current playing."""

        player: Player = self.bot.get_player_instance(ctx.guild.id)

        if not player.current:
            await ctx.send(embed=Embed(t('music.no_song_playing')), ephemeral=True)
            return

        now_playing = player.current

        footer = player.messager.get_footer(now_playing)
        footer.pop(1)

        embed = Embed()
        embed.add_field(t('music.nowplaying.uploader'), now_playing.author)
        embed.add_field(t('music.nowplaying.duration'), format_milliseconds(now_playing.duration))
        embed.set_author(
            name=now_playing.title,
            url=now_playing.uri,
            icon_url=ICONS['music'],
        )
        embed.set_image(url=now_playing.artwork_url)
        embed.set_footer(text=' | '.join(footer), icon_url=self.bot.get_user(now_playing.requester).display_avatar.url)
        await ctx.reply(embed=embed)

    @app_commands.command(name='playlist')
    @has_permission()
    @in_voice()
    @has_player()
    @commands.guild_only()
    async def playlist(self, interaction: discord.Interaction['NeonBot']) -> None:
        """List down all songs in the player's queue."""

        player: Player = self.bot.get_player_instance(interaction.guild_id)
        embeds = []
        duration = 0

        if len(player.track_list) == 0:
            await interaction.response.send_message(
                embed=Embed(t('music.empty_playlist')), ephemeral=True
            )
            return

        for i in range(0, len(player.playlist), 10):
            temp = []
            for _, track in enumerate(player.playlist[i: i + 10], i):
                title = f'`{"*" if player.current.identifier == track.identifier else ""}{track.extra["index"] + 1}.` [{track["title"]}]({track["uri"]})'
                description = f"""\
{title}
- - - `{format_milliseconds(track.duration) if track.duration else 'N/A'}` `{self.bot.get_user(track.requester)}`"""

                duration += track.duration or 0

                temp.append(description)
            embeds.append(Embed('\n'.join(temp)))

        footer = [
            t('music.songs', count=len(player.playlist)),
            format_milliseconds(duration),
            t('music.shuffle_footer', shuffle='on' if player.shuffle else 'off'),
            t('music.repeat_footer', repeat=Repeat(player.loop).name.lower()),
        ]

        pagination = PaginationEmbed(interaction, embeds=embeds)
        pagination.embed.set_author(name=t('music.player_queue'), icon_url=ICONS['music'])
        pagination.embed.set_footer(text=' | '.join(footer), icon_url=self.bot.user.display_avatar)
        await pagination.build(page_number=player.current.extra['index'] // 10 + 1)

    @commands.hybrid_command(name='goto', aliases=['jump', 'go'])
    @has_permission()
    @in_voice()
    @has_player()
    @commands.guild_only()
    async def goto(self, ctx: commands.Context['NeonBot'], index: int) -> None:
        """Skips the current song."""

        player: Player = self.bot.get_player_instance(ctx.guild.id)

        try:
            player.current_queue = index - 1
            track = player.track_list[player.current_queue]

            await ctx.reply(embed=Embed(t('music.jumped_to', index=index, title=track.title, url=track.uri)))

            await player.play(track)
        except IndexError:
            await ctx.reply(embed=Embed(t('music.invalid_index')), ephemeral=True)

    @commands.hybrid_command(name='removesong', aliases=['remove', 'del', 'rm'])
    @has_permission()
    @in_voice()
    @has_player()
    @commands.guild_only()
    async def removesong(self, ctx: commands.Context['NeonBot'], index: int) -> None:
        """Removes a specific song."""

        player: Player = self.bot.get_player_instance(ctx.guild.id)

        try:
            is_currently_playing = player.current.extra['index'] == index - 1
            removed = player.remove(index - 1)

            if len(player.playlist) > 0 and is_currently_playing:
                await player.prev()

            await ctx.reply(embed=Embed(t('music.removed_song', index=index, title=removed.title, url=removed.uri)))

            if len(player.playlist) == 0:
                await player.reset()
        except IndexError:
            await ctx.reply(embed=Embed(t('music.invalid_index')), ephemeral=True)

    @commands.hybrid_command(name='reset')
    @has_permission()
    @in_voice()
    @has_player()
    @commands.guild_only()
    async def reset(self, ctx: commands.Context['NeonBot']) -> None:
        """Resets the current player and disconnect to voice channel."""

        player: Player = self.bot.get_player_instance(ctx.guild.id)
        await player.reset()

        msg = t('music.player_reset')
        log.cmd(ctx, msg)
        await ctx.reply(embed=Embed(msg))

    @commands.hybrid_command(name='join')
    @has_permission()
    @commands.guild_only()
    async def join(self, ctx: commands.Context['NeonBot'], voice_channel: discord.VoiceChannel) -> None:
        """Connect to voice channel."""

        player: Player = await self.bot.create_player_instance(ctx.guild.id, ctx=ctx)
        await player.connect(voice_channel)

        await ctx.reply(embed=Embed(t('music.joined_channel', channel=voice_channel.mention)), ephemeral=True)

    @commands.hybrid_command(name='leave')
    @has_permission()
    @commands.guild_only()
    async def leave(self, ctx: commands.Context['NeonBot']) -> None:
        """Connect to voice channel."""

        player: Player = self.bot.get_player_instance(ctx.guild.id)

        last_voice_channel = player.voice_channel

        await player.disconnect()

        await ctx.reply(embed=Embed(t('music.left_channel', channel=last_voice_channel.mention)), ephemeral=True)

    @commands.hybrid_command(name='shuffle')
    @has_permission()
    @commands.guild_only()
    async def shuffle(self, ctx: commands.Context['NeonBot'], state: bool) -> None:
        """Set shuffle mode."""

        player: Player = self.bot.get_player_instance(ctx.guild.id)
        player.set_shuffle(state)

        user = ctx.author.mention if ctx.invoked_with != 'bot' else ctx.guild.me.mention
        await ctx.reply(embed=Embed(t('music.shuffle_changed', mode='on' if player.shuffle else 'off', user=user)))

    @commands.hybrid_command(name='repeat')
    @has_permission()
    @commands.guild_only()
    @app_commands.choices(mode=[
        app_commands.Choice(name='Off', value=0),
        app_commands.Choice(name='Single', value=1),
        app_commands.Choice(name='All', value=2),
    ])
    async def repeat(self, ctx: commands.Context['NeonBot'], mode: int) -> None:
        """Set repeat mode."""

        player: Player = self.bot.get_player_instance(ctx.guild.id)

        modes = [Repeat.OFF, Repeat.SINGLE, Repeat.ALL]
        player.set_loop(modes[mode].value)

        user = ctx.author.mention if ctx.invoked_with != 'bot' else ctx.guild.me.mention
        await ctx.reply(embed=Embed(t('music.repeat_changed', mode=modes[mode].name.lower(), user=user)))

    @commands.hybrid_command(name='autoplay')
    @has_permission()
    @commands.guild_only()
    async def autoplay(self, ctx: commands.Context['NeonBot'], state: bool) -> None:
        """Set autoplay mode."""

        player: Player = self.bot.get_player_instance(ctx.guild.id)
        player.set_autoplay(state)

        user = ctx.author.mention if ctx.invoked_with != 'bot' else ctx.guild.me.mention
        await ctx.reply(embed=Embed(t('music.autoplay_changed', mode='on' if player.autoplay else 'off', user=user)))


async def setup(bot: 'NeonBot') -> None:
    await bot.add_cog(Music(bot))
