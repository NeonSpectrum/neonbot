from time import time
from urllib.parse import urlparse

from addict import Dict

from .. import bot, env
from ..helpers.exceptions import ApiError

spotify_credentials = Dict()


class Spotify:
    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self) -> None:
        self.session = bot.session
        self.client_id = env.str("SPOTIFY_CLIENT_ID")
        self.client_secret = env.str("SPOTIFY_CLIENT_SECRET")

    async def get_token(self) -> str:
        if spotify_credentials.expiration and time() < spotify_credentials.expiration:
            return spotify_credentials.token

        res = await self.session.post(
            f"https://{self.client_id}:{self.client_secret}@accounts.spotify.com/api/token",
            params={"grant_type": "client_credentials"},
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        json = Dict(await res.json())

        if json.error_description:
            raise ApiError(json.error_description)

        spotify_credentials.token = json.access_token
        spotify_credentials.expiration = time() + json.expires_in - 600

        return spotify_credentials.token

    def parse_url(self, url: str) -> Dict:
        parsed = urlparse(url)
        scheme = parsed.scheme
        hostname = parsed.netloc
        path = parsed.path

        try:
            if hostname == "open.spotify.com" or "open.spotify.com" in path:
                url_type, url_id = path.split("/")[1:3]
            elif scheme == "spotify":
                url_type, url_id = path.split(":")
            if not url_type or not url_id:
                raise ValueError
        except ValueError:
            return Dict()

        return Dict(id=url_id, type=url_type)

    async def get_track(self, track_id: str) -> Dict:
        token = await self.get_token()

        res = await self.session.get(
            self.BASE_URL + "/tracks/" + track_id,
            headers={"Authorization": f"Bearer {token}"},
        )
        return Dict(await res.json())

    async def get_playlist(self, playlist_id: str) -> Dict:
        token = await self.get_token()
        playlist = []

        limit = 100
        offset = 0

        while True:
            res = await self.session.get(
                self.BASE_URL + "/playlists/" + playlist_id + '/tracks',
                headers={"Authorization": f"Bearer {token}"},
                params={"offset": offset, "limit": limit}
            )
            data = Dict(await res.json())
            print(data)
            playlist += data['items']

            if data.next is None:
                break

            offset += limit

        return playlist
