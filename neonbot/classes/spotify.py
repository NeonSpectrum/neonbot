from time import time
from typing import Optional
from urllib.parse import urlparse

import discord
from aiohttp import ClientSession, ClientTimeout
from envparse import env
from i18n import t

from .embed import Embed
from .player import Player
from .with_interaction import WithInteraction
from .ytdl import ytdl
from ..utils.exceptions import ApiError


class Spotify(WithInteraction):
    CREDENTIALS = {
        'token': None,
        'expiration': 0
    }
    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, interaction: discord.Interaction) -> None:
        super().__init__(interaction)
        self.session = ClientSession(timeout=ClientTimeout(total=10))
        self.client_id = env.str("SPOTIFY_CLIENT_ID")
        self.client_secret = env.str("SPOTIFY_CLIENT_SECRET")

    async def get_token(self) -> Optional[str]:
        if Spotify.CREDENTIALS['expiration'] and time() < Spotify.CREDENTIALS['expiration']:
            return Spotify.CREDENTIALS['token']

        res = await self.session.post(
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

    async def get_playlist(self, playlist_id: str, url_type: str) -> list:
        playlist = []

        if url_type == "album":
            limit = 50
            url_prefix = "/albums"
        else:
            limit = 100
            url_prefix = "/playlists"

        offset = 0

        while True:
            res = await self.request(
                url_prefix + "/" + playlist_id + '/tracks',
                params={"offset": offset, "limit": limit}
            )
            data = await res.json()

            if 'items' not in data:
                break

            playlist += data['items']

            if data['next'] is None:
                break

            offset += limit

        return playlist

    async def get_album(self, playlist_id: str) -> list:
        playlist = []

        limit = 100
        offset = 0

        while True:
            res = await self.request(
                "/albums/" + playlist_id + '/tracks',
                params={"offset": offset, "limit": limit}
            )
            data = await res.json()

            if 'items' not in data:
                break

            playlist += data['items']

            if data['next'] is None:
                break

            offset += limit

        return playlist

    async def request(self, url: str, params: dict = None):
        token = await self.get_token()

        return await self.session.get(
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
        data = []
        error = 0

        if is_playlist or is_album:
            await self.send_message(embed=Embed(t('music.converting_to_youtube_playlist')))
            playlist = await self.get_playlist(url['id'], url["type"])
        else:
            await self.send_message(embed=Embed(t('music.converting_to_youtube_track')))
            playlist.append(await self.get_track(url['id']))

        if len(playlist) == 0:
            await self.send_message(embed=Embed(t('music.youtube_no_song')))
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
            await self.send_message(embed=Embed(t('music.youtube_failed_to_find_similar')))
            return

        if is_playlist or is_album:
            await self.send_message(embed=Embed(
                t('music.added_multiple_to_queue', count=len(data)) + t('music.added_failed', count=error)
            ))
        else:
            await self.send_message(embed=Embed(
                t('music.added_to_queue', queue=len(player.queue) + 1, title=data[0]['title'], url=data[0]['url'])
            ))

        player.add_to_queue(data, requested=self.interaction.user)
