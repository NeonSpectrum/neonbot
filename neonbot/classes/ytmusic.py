import functools
import random
from typing import List

from ytmusicapi import YTMusic

from neonbot import bot

YTMUSIC_COUNTRY = 'PH'
ytmusic = YTMusic(location=YTMUSIC_COUNTRY)


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

        browser_id = watch_playlist['related']

        try:
            if not browser_id:
                raise Exception('Browse id not found.')

            song_related = await bot.loop.run_in_executor(
                bot.executor,
                functools.partial(ytmusic.get_song_related, browser_id),
            )
            tracks = song_related[0].get('contents', [])
        except Exception:
            tracks = watch_playlist.get('tracks', [])

        related_tracks = []

        for track in tracks[1:]:
            if track.get('videoId'):
                related_tracks.append({'id': track.get('videoId'), 'title': track.get('title')})
            else:
                related_tracks.append({'id': track.get('counterpart')['videoId'], 'title': track.get('title')})

        return related_tracks

    @staticmethod
    async def get_top_playlist() -> List[dict]:
        playlist_id = 'PLFcGX84jKOu5_K-w5jo9KkmrVvWzBMv-F'

        playlist = await bot.loop.run_in_executor(
            bot.executor,
            functools.partial(ytmusic.get_playlist, playlist_id),
        )

        tracks = []

        playlist_tracks = playlist.get('tracks')

        random.shuffle(playlist_tracks)

        for track in playlist_tracks:
            if track.get('videoId'):
                tracks.append({'id': track.get('videoId'), 'title': track.get('title')})
            else:
                tracks.append({'id': track.get('counterpart')['videoId'], 'title': track.get('title')})

        return tracks
