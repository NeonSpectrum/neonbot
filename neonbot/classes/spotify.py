from time import time
from typing import Optional
from urllib.parse import urlparse

from ..helpers.exceptions import ApiError


class Spotify:
    CREDENTIALS = {
        'token': None,
        'expiration': 0
    }
    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, bot) -> None:
        self.session = bot.session
        self.client_id = bot.env.str("SPOTIFY_CLIENT_ID")
        self.client_secret = bot.env.str("SPOTIFY_CLIENT_SECRET")

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
            url_prefix = "/albums"
        else:
            url_prefix = "/playlists"

        limit = 100
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
