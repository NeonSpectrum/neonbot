from time import time
from typing import Optional, Tuple
from urllib.parse import urlparse

import discord
from envparse import env
from i18n import t

from .embed import Embed
from .player import Player
from .with_interaction import WithInteraction
from .ytdl import ytdl
from .. import bot
from ..utils.exceptions import ApiError


class Spotify(WithInteraction):
    CREDENTIALS = {
        'token': None,
        'expiration': 0
    }
    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, interaction: discord.Interaction) -> None:
        super().__init__(interaction)
        self.client_id = env.str("SPOTIFY_CLIENT_ID")
        self.client_secret = env.str("SPOTIFY_CLIENT_SECRET")

    async def get_token(self) -> Optional[str]:
        if Spotify.CREDENTIALS['expiration'] and time() < Spotify.CREDENTIALS['expiration']:
            return Spotify.CREDENTIALS['token']

        res = await bot.session.post(
            f"https://{self.client_id}:{self.client_secret}@accounts.spotify.com/api/token",
            params={"grant_type": "client_credentials"},
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        data = await res.json()

        if data.get('error_description'):
            raise ApiError(data['error_description'])

        Spotify.CREDENTIALS['token'] = data['access_token']
        Spotify.CREDENTIALS['expiration'] = time() + data['expires_in'] - 600

        return Spotify.CREDENTIALS['token']

    def parse_url(self, url: str) -> Optional[dict]:
        parsed = urlparse(url)
        scheme = parsed.scheme
        hostname = parsed.netloc
        path = parsed.path
        url_type = None
        url_id = None

        try:
            if hostname == "open.spotify.com" or "open.spotify.com" in path:
                url_type, url_id = path.split("/")[-2:]
            elif scheme == "spotify":
                url_type, url_id = path.split(":")
            if not url_type or not url_id:
                raise ValueError
        except ValueError:
            return None

        return dict(id=url_id, type=url_type)

    async def get_track(self, track_id: str) -> dict:
        res = await self.request("/tracks/" + track_id)
        return await res.json()

    async def get_playlist(self, playlist_id: str, url_type: str) -> Tuple[list, dict]:
        playlist = []
        playlist_info = None

        if url_type == "album":
            limit = 50
            url_prefix = "/albums"
        else:
            limit = 100
            url_prefix = "/playlists"

        offset = 0

        while True:
            res = await self.request(
                url_prefix + "/" + playlist_id,
                params={"offset": offset, "limit": limit}
            )
            data = await res.json()

            if 'items' not in data['tracks']:
                break

            playlist_info = self.get_playlist_info(data)

            playlist += data['tracks']['items']

            if data['tracks']['next'] is None:
                break

            offset += limit

        return playlist, playlist_info

    async def request(self, url: str, params: dict = None):
        token = await self.get_token()

        return await bot.session.get(
            Spotify.BASE_URL + url,
            headers={"Authorization": f"Bearer {token}"},
            params=params
        )

    async def search_url(self, url: str) -> None:
        url = self.parse_url(url)
        ytdl_one = ytdl.create({"default_search": "ytsearch1"})

        if not url:
            await self.send_message(embed=Embed(t('music.invalid_spotify_url')), ephemeral=True)
            return

        player = await Player.get_instance(self.interaction)

        is_playlist = url['type'] == "playlist"
        is_album = url['type'] == "album"
        playlist = []
        playlist_info = None
        data = []
        error = 0

        if is_playlist or is_album:
            await self.send_message(embed=Embed(t('music.converting_to_youtube_playlist')))
            playlist, playlist_info = await self.get_playlist(url['id'], url["type"])
        else:
            await self.send_message(embed=Embed(t('music.converting_to_youtube_track')))
            playlist.append(await self.get_track(url['id']))

        if len(playlist) == 0:
            await self.send_message(embed=Embed(t('music.youtube_no_song')))
            return

        for item in playlist:
            track = item['track'] if is_playlist else item

            ytdl_info = await ytdl_one.extract_info(
                f"{' '.join(artist['name'] for artist in track['artists'])} {track['name']}",
                process=True
            )

            playlist = ytdl_info.get_list()

            if len(playlist) == 0:
                error += 1
                continue

            data.append(playlist[0])

        if len(data) == 0:
            await self.send_message(embed=Embed(t('music.youtube_failed_to_find_similar')))
            return

        if is_playlist or is_album:
            embed = Embed(
                t('music.added_multiple_to_queue', count=len(data)) + ' ' + t('music.added_failed', count=error)
            )
            embed.set_author(playlist_info.get('title'), playlist_info.get('url'))
            embed.set_image(playlist_info.get('thumbnail'))
            embed.set_footer('Uploaded by: ' + playlist_info.get('uploader'))
        else:
            embed = Embed(
                t('music.added_to_queue', queue=len(player.queue) + 1, title=data[0]['title'], url=data[0]['url'])
            )

        await self.send_message(embed=embed)
        player.add_to_queue(data, requested=self.interaction.user)

    def get_playlist_info(self, data):
        return dict(
            title=data.get('name'),
            url=data.get('external_urls')['spotify'],
            thumbnail=data.get('images')[0]['url'] if len(data.get('images')) > 0 else None,
            uploader=data.get('owner')['display_name'],
        )
