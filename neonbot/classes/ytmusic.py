import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from ytmusicapi import YTMusic

from neonbot import bot

ytmusic = YTMusic()


class YTMusic:
    def __init__(self):
        self.loop = bot.loop

    async def search(self, keyword) -> Optional[int]:
        with ThreadPoolExecutor(max_workers=1) as executor:
            results: list[dict] = await self.loop.run_in_executor(
                executor,
                functools.partial(ytmusic.search, keyword, limit=1, filter='songs'),
            )

        return results[0].get('videoId') if len(results) > 0 else None

    async def get_related_video(self, track: dict, playlist: list = None) -> Optional[int]:
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = await bot.loop.run_in_executor(
                executor,
                functools.partial(ytmusic.get_watch_playlist, track['id'], limit=1),
            )
        tracks = result.get('tracks', [])

        for track in tracks[1:]:
            if playlist and track.get('videoId') in playlist:
                continue

            if track.get('videoType') == 'MUSIC_VIDEO_TYPE_ATV' and track.get('counterpart'):
                return track.get('counterpart')['videoId']

            return track.get('videoId')

        return None
