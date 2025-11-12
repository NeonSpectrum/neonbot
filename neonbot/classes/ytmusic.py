import functools
from typing import Optional

from ytmusicapi import YTMusic

from neonbot import bot

ytmusic = YTMusic()


class YTMusic:
    @staticmethod
    async def search(keyword):
        results: list[dict] = await bot.loop.run_in_executor(
            bot.executor,
            functools.partial(ytmusic.search, keyword, limit=1, filter='songs'),
        )
        result = results[0]

        return result.get('videoId')

    @staticmethod
    async def get_related_video(video_id: str, playlist: list = None) -> Optional[int]:
        result = await bot.loop.run_in_executor(
            bot.executor,
            functools.partial(ytmusic.get_watch_playlist, video_id, limit=1),
        )
        tracks = result.get('tracks', [])

        for track in tracks[1:]:
            if playlist and track.get('videoId') in playlist:
                continue
            
            if not track.get('videoId') and track.get('counterpart'):
                return track.get('counterpart')['videoId']

            return track.get('videoId')

        return None
