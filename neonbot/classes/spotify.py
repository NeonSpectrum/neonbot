import asyncio
import urllib.parse
from time import time
from typing import Optional, Tuple
from urllib.parse import urlparse

import discord
from envparse import env
from i18n import t

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.classes.player import Player
from neonbot.classes.with_interaction import WithInteraction
from neonbot.classes.ytdl import Ytdl
from neonbot.classes.ytmusic import YTMusic
from neonbot.utils import log
from neonbot.utils.exceptions import ApiError, YtdlError


class Spotify(WithInteraction):
    CREDENTIALS = {'token': None, 'expiration': 0}
    BASE_URL = 'https://api.spotify.com/v1'

    def __init__(self, interaction: discord.Interaction) -> None:
        super().__init__(interaction)
        self.client_id = env.str('SPOTIFY_CLIENT_ID')
        self.client_secret = env.str('SPOTIFY_CLIENT_SECRET')

        self.id = None
        self.type = None

    @property
    def url_prefix(self) -> Optional[str]:
        if self.is_album:
            return '/albums'
        elif self.is_playlist:
            return '/playlists'
        elif self.is_track:
            return '/tracks'

        return None

    @property
    def is_playlist(self) -> bool:
        return self.type == 'playlist'

    @property
    def is_album(self) -> bool:
        return self.type == 'album'

    @property
    def is_track(self) -> bool:
        return self.type == 'track'

    async def get_token(self) -> Optional[str]:
        if Spotify.CREDENTIALS['expiration'] and time() < Spotify.CREDENTIALS['expiration']:
            return Spotify.CREDENTIALS['token']

        res = await bot.session.post(
            f'https://{self.client_id}:{self.client_secret}@accounts.spotify.com/api/token',
            params={'grant_type': 'client_credentials'},
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
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
            if hostname == 'open.spotify.com' or 'open.spotify.com' in path:
                url_type, url_id = path.split('/')[-2:]
            elif scheme == 'spotify':
                url_type, url_id = path.split(':')
            if not url_type or not url_id:
                raise ValueError
        except ValueError:
            return None

        return dict(id=url_id, type=url_type)

    async def get_track(self) -> dict:
        return await self.request(self.url_prefix + '/' + self.id)

    async def get_playlist(self) -> Tuple[list, dict]:
        playlist = []

        if self.is_album:
            limit = 50
        else:
            limit = 100

        offset = 0
        playlist_info = await self.get_playlist_info()

        while True:
            data = await self.request(
                self.url_prefix + '/' + self.id + '/tracks', params={'offset': offset, 'limit': limit}
            )

            if 'items' not in data:
                break

            playlist += data['items']

            if data['next'] is None:
                break

            offset += limit

        return playlist, playlist_info

    async def request(self, url: str, params: dict = None):
        token = await self.get_token()

        res = await bot.session.get(Spotify.BASE_URL + url, headers={'Authorization': f'Bearer {token}'}, params=params)

        return await res.json()

    async def search_url(self, url: str) -> None:
        url = self.parse_url(url)

        if not url:
            await self.send_message(embed=Embed(t('music.invalid_spotify_url')), ephemeral=True)
            return

        player = await Player.get_instance(self.interaction)

        playlist = []
        playlist_info = None

        self.id = url['id']
        self.type = url['type']

        if self.is_playlist or self.is_album:
            await self.send_message(embed=Embed(t('music.converting_to_youtube_playlist')))
            playlist, playlist_info = await self.get_playlist()
        elif self.is_track:
            await self.send_message(embed=Embed(t('music.converting_to_youtube_track')))
            playlist.append(await self.get_track())
        else:
            await self.send_message(embed=Embed(t('music.invalid_spotify_type')))
            return

        if len(playlist) == 0:
            await self.send_message(embed=Embed(t('music.youtube_no_song')))
            return

        data = await self.process_playlist(playlist)

        if len(data) == 0:
            await self.send_message(embed=Embed(t('music.youtube_failed_to_find_similar')))
            return

        if self.is_playlist or self.is_album:
            embed = Embed(
                t('music.added_multiple_to_queue', count=len(data))
                + ' '
                + t('music.added_failed', count=len(playlist) - len(data))
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

    async def get_playlist_info(self):
        uploader = None

        data = await self.request(self.url_prefix + '/' + self.id, params={'fields': 'name,external_urls,images,owner'})

        try:
            if self.is_playlist:
                uploader = data.get('owner')['display_name']
            elif self.is_album:
                uploader = ', '.join(map(lambda artist: artist['name'], data.get('artists', [])))

            return dict(
                title=data.get('name'),
                url=data.get('external_urls')['spotify'],
                thumbnail=data.get('images')[0]['url'] if len(data.get('images')) > 0 else None,
                uploader=uploader,
            )
        except TypeError:
            log.error('Cannot parse playlist info: ' + str(data))

            return None

    async def process_playlist(self, playlist):
        async def search(item):
            track = item['track'] if self.is_playlist else item

            try:
                keyword = f'{" ".join(artist["name"] for artist in track["artists"])} {track["name"]}'

                track = await YTMusic().search(keyword)

                if not track.get('id'):
                    raise YtdlError()
            except YtdlError:
                return None

            return track

        data = await asyncio.gather(*[search(item) for item in playlist])

        return list(filter(None, data))
