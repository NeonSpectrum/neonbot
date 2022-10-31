from typing import Optional

import discord
from discord import app_commands
from discord.app_commands.models import Choice
from discord.ext import commands
from i18n import t

from neonbot import bot
from neonbot.classes.embed import Embed, PaginationEmbed
from neonbot.classes.player import Player
from neonbot.classes.spotify import Spotify
from neonbot.classes.youtube import Youtube
from neonbot.enums import PlayType, Repeat
from neonbot.utils import log
from neonbot.utils.constants import ICONS
from neonbot.utils.functions import format_seconds


async def in_voice(interaction: discord.Interaction) -> bool:
    if await bot.is_owner(interaction.user) and interaction.command.name == "reset":
        return True

    if not interaction.user.voice:
        await interaction.response.send_message(embed=Embed("You need to be in the channel."), ephemeral=True)
        return False
    return True


async def has_player(interaction: discord.Interaction) -> bool:
    player = await Player.get_instance(interaction)

    if not player.connection:
        await interaction.response.send_message(embed=Embed("No active player."), ephemeral=True)
        return False
    return True


class Music(commands.Cog):
    @app_commands.command(name='play')
    @app_commands.rename(play_type='type')
    @app_commands.describe(
        play_type='Select type...',
        value='Enter keyword or url...'
    )
    @app_commands.choices(play_type=[
        Choice(name='YouTube Search', value=PlayType.SEARCH.value),
        Choice(name='YouTube URL', value=PlayType.YOUTUBE.value),
        Choice(name='Spotify URL', value=PlayType.SPOTIFY.value),
    ])
    @app_commands.check(in_voice)
    @app_commands.guild_only()
    async def play(
        self,
        interaction: discord.Interaction,
        play_type: PlayType,
        value: str,
        play_now: Optional[bool] = False
    ):
        """Searches the url or the keyword and add it to queue."""

        player = await Player.get_instance(interaction)
        last_index = len(player.queue)

        if play_type == PlayType.SEARCH:
            await Youtube(interaction).search_keyword(value)
        elif play_type == PlayType.YOUTUBE:
            await Youtube(interaction).search_url(value)
        elif play_type == PlayType.SPOTIFY:
            await Spotify(interaction).search_url(value)

        if play_now and player.connection.is_playing():
            player.jump(last_index + 1)
        elif len(player.queue) > 0:
            await player.connect()
            await player.play()

    @app_commands.command(name='nowplaying')
    @app_commands.check(in_voice)
    @app_commands.guild_only()
    async def nowplaying(self, interaction: discord.Interaction) -> None:
        """Displays in brief description of the current playing."""

        player = await Player.get_instance(interaction)

        if not player.connection or not player.connection.is_playing():
            await interaction.response.send_message(embed=Embed(t('music.no_song_playing')), ephemeral=True)
            return

        now_playing = player.now_playing

        footer = player.get_footer(now_playing)
        footer.pop(1)

        embed = Embed()
        embed.add_field(t('music.nowplaying.uploader'), now_playing['uploader'])
        embed.add_field(t('music.nowplaying.upload_date'), now_playing['upload_date'])
        embed.add_field(t('music.nowplaying.duration'), now_playing['formatted_duration'])
        embed.add_field(t('music.nowplaying.views'), now_playing['view_count'])
        embed.add_field(t('music.nowplaying.description'), now_playing['description'], inline=False)
        embed.set_author(
            name=now_playing['title'],
            url=now_playing['url'],
            icon_url=ICONS['music'],
        )
        embed.set_thumbnail(url=now_playing['thumbnail'])
        embed.set_footer(
            text=" | ".join(footer), icon_url=now_playing['requested'].display_avatar
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='playlist')
    @app_commands.check(in_voice)
    @app_commands.guild_only()
    async def playlist(self, interaction: discord.Interaction) -> None:
        """List down all songs in the player's queue."""

        player = await Player.get_instance(interaction)
        queue = player.queue
        embeds = []
        duration = 0

        if not queue:
            await interaction.response.send_message(embed=Embed(t('music.empty_playlist')), ephemeral=True)
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
            t('music.songs', count=len(player.queue)),
            format_seconds(duration),
            t('music.volume_footer', volume=player.volume),
            t('music.shuffle_footer', shuffle='on' if player.is_shuffle else 'off'),
            t('music.repeat_footer', repeat=Repeat(player.repeat).name.lower()),
        ]

        pagination = PaginationEmbed(interaction, embeds=embeds)
        pagination.embed.set_author(
            name=t('music.player_queue'), icon_url=ICONS['music']
        )
        pagination.embed.set_footer(
            text=" | ".join(footer), icon_url=bot.user.display_avatar
        )
        await pagination.build()

    @app_commands.command(name='volume')
    @app_commands.check(in_voice)
    @app_commands.guild_only()
    async def volume(self, interaction: discord.Interaction, volume: app_commands.Range[int, 1, 100]) -> None:
        """Sets or gets player's volume."""

        player = await Player.get_instance(interaction)

        if volume < 1 or volume > 100:
            await interaction.response.send_message(embed=Embed(t('music.volume_rules')), ephemeral=True)
            return

        await player.set_volume(volume)
        await interaction.response.send_message(embed=Embed(t('music.volume_changed', volume=volume)))

    @app_commands.command(name='jump')
    @app_commands.check(in_voice)
    @app_commands.check(has_player)
    @app_commands.guild_only()
    async def jump(self, interaction: discord.Interaction, index: int) -> None:
        """Skips the current song."""

        player = await Player.get_instance(interaction)

        if index > len(player.queue) or index < 0:
            await interaction.response.send_message(embed=Embed("Invalid index."), ephemeral=True)
            return

        player.jump(index)
        track = player.get_track(index - 1)

        await interaction.response.send_message(
            embed=Embed(t('music.jumped_to', index=index, title=track['title'], url=track['url']))
        )

    @app_commands.command(name='reset')
    @app_commands.check(in_voice)
    @app_commands.check(has_player)
    @app_commands.guild_only()
    async def reset(self, interaction: discord.Interaction) -> None:
        """Resets the current player and disconnect to voice channel."""

        player = await Player.get_instance(interaction)
        await player.reset()
        player.remove_instance()

        msg = "Player reset."
        log.cmd(interaction, msg)
        await interaction.response.send_message(embed=Embed(msg))


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music())
