from __future__ import annotations

from typing import Optional

import discord
from i18n import t

from neonbot import bot
from neonbot.classes.embed import Embed, EmbedChoices
from neonbot.classes.player import Player
from neonbot.classes.spotify import spotify
from neonbot.classes.youtube import youtube
from neonbot.classes.ytdl import ytdl
from neonbot.utils.exceptions import YtdlError


class PlayerHandler:
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self._player: Optional[Player] = None

    async def get_player(self) -> Player:
        ctx = await bot.get_context(self.interaction)
        self._player = Player.get_instance(ctx)
        return self._player

    async def send_message(self, *args, **kwargs):
        await bot.send_response(self.interaction, *args, view=None, **kwargs)

    async def search_keyword(self, keyword: str):
        try:
            data = await youtube.get_info(keyword, process=True)
        except YtdlError:
            await self.interaction.response.send_message(embed=Embed(t('music.no_songs_available')), ephemeral=True)
            return

        choice = (await EmbedChoices(self.interaction, youtube.beautify_choices(data)).build()).value

        if choice < 0:
            await self.interaction.delete_original_response()
            return

        info = data[choice]

        await self.send_message(embed=Embed(
            t('music.added_to_queue', queue=len(self._player.queue) + 1, title=info['title'], url=info['url'])
        ))

        self._player.add_to_queue(info, requested=self.interaction.user)

    async def search_youtube(self, url: str):
        data = await youtube.get_info(url, process=False)

        if isinstance(data, list):
            data = youtube.get_playlist(data)
            await self.send_message(embed=Embed(t('music.added_multiple_to_queue', count=len(data))))
        elif isinstance(data, dict):
            await self.send_message(embed=Embed(
                t('music.added_to_queue', queue=len(self._player.queue) + 1, title=data['title'], url=data['url'])
            ))
        else:
            await self.send_message(embed=Embed(t('music.song_failed_to_load')), ephemeral=True)

        self._player.add_to_queue(data, requested=self.interaction.user)

    async def search_spotify(self, url: str) -> None:
        url = spotify.parse_url(url)
        ytdl_one = ytdl.create({"default_search": "ytsearch1"})

        if not url:
            await self.send_message(embed=Embed(t('music.invalid_spotify_url')), ephemeral=True)
            return

        is_playlist = url['type'] == "playlist"
        is_album = url['type'] == "album"
        playlist = []
        data = []
        error = 0

        if is_playlist or is_album:
            await self.send_message(embed=Embed(t('music.converting_to_youtube_playlist')), ephemeral=True)
            playlist = await spotify.get_playlist(url['id'], url["type"])
        else:
            await self.send_message(embed=Embed(t('music.converting_to_youtube_track')), ephemeral=True)
            playlist.append(await spotify.get_track(url['id']))

        if len(playlist) == 0:
            await self.send_message(embed=Embed(t('music.youtube_no_song')),
                                    ephemeral=True)
            return

        for item in playlist:
            track = item['track'] if is_playlist else item
            info = await ytdl_one.extract_info(
                f"{' '.join(artist['name'] for artist in track['artists'])} {track['name']}",
                process=True
            )

            if info is None:
                error += 1
                continue

            data.append(info)

        if len(data) == 0:
            await self.send_message(embed=Embed(t('music.youtube_failed_to_find_similar')), ephemeral=True)
            return

        if is_playlist or is_album:
            await self.send_message(embed=Embed(
                t('music.added_multiple_to_queue', count=len(data)) + t('music.added_failed', count=error)
            ))
        else:
            await self.send_message(embed=Embed(
                t('music.added_to_queue', queue=len(self._player.queue) + 1, title=data[0]['title'], url=data[0]['url'])
            ))

        self._player.add_to_queue(data, requested=self.interaction.user)
