import functools
from concurrent.futures import ThreadPoolExecutor
from time import time
from typing import Optional

from ytmusicapi import YTMusic

from neonbot import bot
from neonbot.classes.ytdl_info import YtdlInfo
from neonbot.utils import log

ytmusic = YTMusic()


class YTMusic:
    def __init__(self):
        self.loop = bot.loop

    async def search(self, keyword) -> YtdlInfo:
        start_time = time()
        results: list[dict] = await self.loop.run_in_executor(
            bot.executor,
            functools.partial(ytmusic.search, keyword, limit=1, filter='songs'),
        )
        log.info(f'ytmusic.search finished after {(time() - start_time):.2f}s')

        result = results[0]

        return YtdlInfo(
            {
                'id': result.get('videoId'),
                'title': result.get('title'),
                'duration': result.get('duration_seconds'),
                'original_url': 'https://music.youtube.com/watch?v=' + result.get('videoId'),
            }
        )

    async def get_related_video(self, track: dict, playlist: list = None) -> Optional[int]:
        result = await bot.loop.run_in_executor(
            bot.executor,
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
