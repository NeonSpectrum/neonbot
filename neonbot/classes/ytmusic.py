import functools
import random
from typing import List

from envparse import env
from ytmusicapi import YTMusic, OAuthCredentials, LikeStatus

from neonbot import bot
from neonbot.utils import log

YTMUSIC_COUNTRY = env.str('YTMUSIC_COUNTRY')
YTMUSIC_CREDENTIALS_TYPE = env.str('YTMUSIC_CREDENTIALS_TYPE')

if YTMUSIC_CREDENTIALS_TYPE == 'browser':
    ytmusic = YTMusic(
        env.str('YTMUSIC_CREDENTIALS_JSON'),
        env.str('YTMUSIC_BRAND_ACCOUNT_ID'),
        location=YTMUSIC_COUNTRY
    )
elif YTMUSIC_CREDENTIALS_TYPE == 'oauth':
    ytmusic = YTMusic(
        env.str('YTMUSIC_CREDENTIALS_JSON'),
        env.str('YTMUSIC_BRAND_ACCOUNT_ID'),
        oauth_credentials=OAuthCredentials(client_id=env.str('YTMUSIC_CLIENT_ID'), client_secret=env.str('YTMUSIC_CLIENT_SECRET')),
        location=YTMUSIC_COUNTRY
    )
else:
    ytmusic = YTMusic(
        location=YTMUSIC_COUNTRY
    )


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
    async def get_random_song() -> List[dict]:
        homes = await bot.loop.run_in_executor(
            bot.executor,
            functools.partial(ytmusic.get_home),
        )

        tracks = []

        for home in homes:
            if home.get('title') == 'Quick picks':
                tracks = home.get('contents')
                break

        home_tracks = []

        for track in tracks:
            if track.get('videoId'):
                home_tracks.append({'id': track.get('videoId'), 'title': track.get('title')})
            else:
                home_tracks.append({'id': track.get('counterpart')['videoId'], 'title': track.get('title')})

        return home_tracks

    @staticmethod
    async def like_song(video_id: str) -> None:
        try:
            await bot.loop.run_in_executor(
                bot.executor,
                functools.partial(ytmusic.rate_song, video_id, LikeStatus.LIKE),
            )
        except Exception as error:
            log.debug(error, exc_info=True)
            log.error('Failed to like song. ' + str(error))

    @staticmethod
    async def get_account_info():
        return await bot.loop.run_in_executor(
            bot.executor,
            functools.partial(ytmusic.get_account_info),
        )