import asyncio
from typing import List, Optional
from typing import TYPE_CHECKING

from ytmusicapi import YTMusic, OAuthCredentials, LikeStatus

from neonbot.env import (
    YTMUSIC_CREDENTIALS_TYPE,
    YTMUSIC_CREDENTIALS_JSON,
    YTMUSIC_BRAND_ACCOUNT_ID,
    YTMUSIC_COUNTRY,
    YTMUSIC_CLIENT_ID,
    YTMUSIC_CLIENT_SECRET
)
from neonbot.utils import log

if TYPE_CHECKING:
    from neonbot import NeonBot

_instance: Optional[YTMusic] = None


def _get_ytmusic() -> Optional[YTMusic]:
    global _instance
    if _instance is not None:
        return _instance
    try:
        if YTMUSIC_CREDENTIALS_TYPE == 'browser':
            _instance = YTMusic(
                YTMUSIC_CREDENTIALS_JSON,
                YTMUSIC_BRAND_ACCOUNT_ID,
                location=YTMUSIC_COUNTRY
            )
        elif YTMUSIC_CREDENTIALS_TYPE == 'oauth':
            _instance = YTMusic(
                YTMUSIC_CREDENTIALS_JSON,
                YTMUSIC_BRAND_ACCOUNT_ID,
                oauth_credentials=OAuthCredentials(
                    client_id=YTMUSIC_CLIENT_ID,
                    client_secret=YTMUSIC_CLIENT_SECRET
                ),
                location=YTMUSIC_COUNTRY
            )
        else:
            _instance = YTMusic(location=YTMUSIC_COUNTRY)
    except Exception as error:
        log.error(f'Failed to initialize YTMusic: {error}')
        _instance = None
    return _instance


def reset_instance():
    global _instance
    _instance = None


class YTMusicHelper:
    def __init__(self, bot: 'NeonBot'):
        self.bot = bot

    async def search(self, keyword) -> Optional[str]:
        try:
            client = _get_ytmusic()
            if not client:
                return None
            results: list[dict] = await asyncio.to_thread(
                client.search, keyword, limit=1, filter='songs'
            )
            if not results:
                return None
            return results[0].get('videoId')
        except Exception as error:
            log.error(f'YTMusic search failed: {error}')
            return None

    async def get_related_tracks(self, video_id: str) -> List[dict]:
        try:
            client = _get_ytmusic()
            if not client or not video_id:
                return []
            watch_playlist = await asyncio.to_thread(
                client.get_watch_playlist, video_id
            )
            tracks = watch_playlist.get('tracks', [])
            related_tracks = []
            for track in tracks[1:]:
                if track.get('videoId'):
                    related_tracks.append({'id': track['videoId'], 'title': track.get('title')})
                elif track.get('counterpart') and track['counterpart'].get('videoId'):
                    related_tracks.append({'id': track['counterpart']['videoId'], 'title': track.get('title')})
            return related_tracks
        except Exception as error:
            log.error(f'YTMusic get_related_tracks failed: {error}')
            return []

    async def get_random_tracks(self) -> List[dict]:
        try:
            client = _get_ytmusic()
            if not client:
                return []
            homes = await asyncio.to_thread(client.get_home)
            tracks = []
            for home in homes:
                contents = home.get('contents', [])
                if contents and any(item.get('videoId') for item in contents if isinstance(item, dict)):
                    tracks = contents
                    break
            home_tracks = []
            for track in tracks:
                if not isinstance(track, dict):
                    continue
                if track.get('videoId'):
                    home_tracks.append({'id': track['videoId'], 'title': track.get('title')})
                elif track.get('counterpart') and track['counterpart'].get('videoId'):
                    home_tracks.append({'id': track['counterpart']['videoId'], 'title': track.get('title')})
            return home_tracks
        except Exception as error:
            log.error(f'YTMusic get_random_tracks failed: {error}')
            return []

    async def like_song(self, video_id: str) -> None:
        try:
            client = _get_ytmusic()
            if not client:
                return
            await asyncio.to_thread(client.rate_song, video_id, LikeStatus.LIKE)
        except Exception as error:
            log.debug(error, exc_info=True)
            log.error(f'Failed to like song: {error}')

    async def get_account_info(self):
        try:
            client = _get_ytmusic()
            if not client:
                return None
            return await asyncio.to_thread(client.get_account_info)
        except Exception as error:
            log.error(f'YTMusic get_account_info failed: {error}')
            return None
