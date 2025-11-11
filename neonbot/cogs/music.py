from typing import cast, Union

import discord
from discord import app_commands
from discord.ext import commands
from i18n import t
from lavalink import listener, TrackEndEvent, TrackStartEvent

from neonbot import bot
from neonbot.classes.embed import Embed, PaginationEmbed
from neonbot.classes.player import Player
from neonbot.enums import Repeat
from neonbot.utils import log
from neonbot.utils.constants import ICONS
from neonbot.utils.functions import format_milliseconds


async def in_voice(ctx: Union[commands.Context, discord.Interaction]) -> bool:
    if isinstance(ctx, discord.Interaction):
        ctx = await bot.get_context(ctx)

    if await bot.is_owner(ctx.author) and ctx.command.name == 'reset':
        return True

    if not ctx.author.voice:
        await ctx.send(
            embed=Embed('You need to be in the channel.'), ephemeral=True
        )
        return False
    return True


async def has_permission(ctx: Union[commands.Context, discord.Interaction]) -> bool:
    if isinstance(ctx, discord.Interaction):
        ctx = await bot.get_context(ctx)

    if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
        await ctx.send(
            embed=Embed("I don't have permission to send message on this channel."), ephemeral=True
        )
        return False
    return True


async def has_player(interaction: discord.Interaction) -> bool:
    player = bot.lavalink.player_manager.get(interaction.guild_id)

    if not player:
        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed('No active player.'), ephemeral=True
        )
        return False
    return True


class Music(commands.Cog):
    def __init__(self):
        bot.lavalink.add_event_hooks(self)

    @commands.command(name='play', aliases=['p'])
    @commands.check(in_voice)
    @commands.check(has_permission)
    async def play(self, ctx, *, query: str):
        await self.handle_play(ctx, query)

    @app_commands.command(name='play')
    @app_commands.describe(query='Enter keyword or url...')
    @app_commands.check(in_voice)
    @app_commands.check(has_permission)
    @app_commands.guild_only()
    async def play_interaction(self, interaction, query: str):
        await self.handle_play(interaction, query)

    async def handle_play(self, ctx: Union[commands.Context, discord.Interaction], query: str):
        """Searches the url or the keyword and add it to queue. This will queue the first search."""

        player = bot.lavalink.player_manager.create(ctx.guild.id)
        player.ctx = await bot.get_context(ctx) if isinstance(ctx, discord.Interaction) else ctx

        await player.search(query)
        await player.connect()

        if not player.is_playing:
            await player.play()

    @app_commands.command(name='nowplaying')
    @app_commands.check(in_voice)
    @app_commands.guild_only()
    async def nowplaying(self, interaction: discord.Interaction) -> None:
        """Displays in brief description of the current playing."""

        player = bot.lavalink.player_manager.get(interaction.guild_id)

        if not player.current:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed(t('music.no_song_playing')), ephemeral=True
            )
            return

        now_playing = player.current

        footer = player.get_footer(now_playing)
        footer.pop(1)

        embed = Embed()
        embed.add_field(t('music.nowplaying.uploader'), now_playing.author)
        embed.add_field(t('music.nowplaying.duration'), format_milliseconds(now_playing.duration))
        embed.set_author(
            name=now_playing.title,
            url=now_playing.uri,
            icon_url=ICONS.music,
        )
        embed.set_thumbnail(url=now_playing.artwork_url)
        embed.set_footer(text=' | '.join(footer), icon_url=bot.get_user(now_playing.requester).display_avatar)
        await cast(discord.InteractionResponse, interaction.response).send_message(embed=embed)

    @app_commands.command(name='playlist')
    @app_commands.check(in_voice)
    @app_commands.guild_only()
    async def playlist(self, interaction: discord.Interaction) -> None:
        """List down all songs in the player's queue."""

        player = bot.lavalink.player_manager.get(interaction.guild_id)
        embeds = []
        duration = 0

        if len(player.track_list) == 0:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed(t('music.empty_playlist')), ephemeral=True
            )
            return

        for i in range(0, len(player.playlist), 10):
            temp = []
            for _, track in enumerate(player.playlist[i: i + 10], i):
                title = f'`{"*" if player.current.identifier == track.identifier else ""}{track.extra['index'] + 1}.` [{track["title"]}]({track["uri"]})'
                description = f"""\
{title}
- - - `{format_milliseconds(track.duration) if track.duration else 'N/A'}` `{bot.get_user(track.requester)}`"""

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
        pagination.embed.set_footer(text=' | '.join(footer), icon_url=bot.user.display_avatar)
        await pagination.build()

    @app_commands.command(name='goto')
    @app_commands.check(in_voice)
    @app_commands.check(has_player)
    @app_commands.guild_only()
    async def goto(self, interaction: discord.Interaction, index: int) -> None:
        """Skips the current song."""

        player = bot.lavalink.player_manager.get(interaction.guild_id)

        try:
            player.current_queue = index - 1
            track = player.track_list[player.current_queue]

            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed(t('music.jumped_to', index=index, title=track.title, url=track.uri))
            )

            await player.play(track)
        except IndexError:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed('Invalid index.'), ephemeral=True
            )

    @app_commands.command(name='removesong')
    @app_commands.check(in_voice)
    @app_commands.check(has_player)
    @app_commands.guild_only()
    async def removesong(self, interaction: discord.Interaction, index: int) -> None:
        """Removes a specific song."""

        player = bot.lavalink.player_manager.get(interaction.guild_id)

        try:
            removed = player.remove(index)

            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed(t('music.removed_song', index=index, title=removed.title, url=removed.uri))
            )
        except IndexError:
            await cast(discord.InteractionResponse, interaction.response).send_message(
                embed=Embed('Invalid index.'), ephemeral=True
            )

    @app_commands.command(name='reset')
    @app_commands.check(in_voice)
    @app_commands.check(has_player)
    @app_commands.guild_only()
    async def reset(self, interaction: discord.Interaction) -> None:
        """Resets the current player and disconnect to voice channel."""

        player = bot.lavalink.player_manager.get(interaction.guild_id)
        await player.reset()

        msg = 'Player reset.'
        log.cmd(interaction, msg)
        await cast(discord.InteractionResponse, interaction.response).send_message(embed=Embed(msg))

    @app_commands.command(name='stop')
    @app_commands.check(in_voice)
    @app_commands.check(has_player)
    @app_commands.guild_only()
    async def stop(self, interaction: discord.Interaction) -> None:
        """Stops the current player and reset the queue from the start."""

        player = bot.lavalink.player_manager.get(interaction.guild_id)
        await player.stop()

        msg = 'Player stopped.'
        log.cmd(interaction, msg)
        await cast(discord.InteractionResponse, interaction.response).send_message(embed=Embed(msg))

    @app_commands.command(name='reconnect')
    @app_commands.check(has_player)
    @app_commands.guild_only()
    async def reconnect(self, interaction: discord.Interaction) -> None:
        """Stops the current player and reset the queue from the start."""

        player = bot.lavalink.player_manager.get(interaction.guild_id)
        await player.disconnect(force=True)
        await player.play()

        msg = 'Player reconnected.'
        log.cmd(interaction, msg)
        await cast(discord.InteractionResponse, interaction.response).send_message(embed=Embed(msg))

    @listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent):
        player = cast(Player, event.player)
        await player.track_start_event(event)

    @listener(TrackEndEvent)
    async def on_track_end(self, event: TrackEndEvent):
        player = cast(Player, event.player)
        await player.track_end_event(event)


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music())
