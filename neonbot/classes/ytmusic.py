import functools
from typing import List

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
    async def get_related_tracks(video_id: str) -> List[dict]:
        watch_playlist = await bot.loop.run_in_executor(
            bot.executor,
            functools.partial(ytmusic.get_watch_playlist, video_id),
        )

        browserId = watch_playlist['related']

        song_related = await bot.loop.run_in_executor(
            bot.executor,
            functools.partial(ytmusic.get_song_related, browserId),
        )

        tracks = song_related[0].get('contents', [])
        related_tracks = []

        for track in tracks[1:]:
            if track.get('videoId'):
                related_tracks.append({'id': track.get('videoId'), 'title': track.get('title')})
            else:
                related_tracks.append({'id': track.get('counterpart')['videoId'], 'title': track.get('title')})

        return related_tracks
