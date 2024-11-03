import functools
from typing import Optional

from neonbot import bot
from ytmusicapi import YTMusic

ytmusic = YTMusic()

class YTMusic:
    def __init__(self):
        self.loop = bot.loop
        self.thread_pool = bot.thread_pool

    async def search(self, keyword) -> Optional[int]:
        results: list[dict] = await self.loop.run_in_executor(
            self.thread_pool,
            functools.partial(ytmusic.search, keyword, limit=1, filter='songs'),
        )

        return results[0].get('videoId') if len(results) > 0 else None

    async def get_related_video(self, track: dict, playlist: list = None) -> Optional[int]:
        result = await bot.loop.run_in_executor(
            bot.thread_pool,
            functools.partial(ytmusic.get_watch_playlist, track['id'], limit=10),
        )
        tracks = result['tracks']

        for track in tracks[1:]:
            if playlist and track['videoId'] in playlist:
                continue

            return track['videoId']

        return None