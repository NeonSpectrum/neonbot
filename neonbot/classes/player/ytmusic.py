import functools
from typing import List
from typing import TYPE_CHECKING

from envparse import env
from ytmusicapi import YTMusic, OAuthCredentials, LikeStatus
from ytmusicapi.exceptions import YTMusicError

from neonbot.utils import log

if TYPE_CHECKING:
    from neonbot import NeonBot

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
        oauth_credentials=OAuthCredentials(client_id=env.str('YTMUSIC_CLIENT_ID'),
                                           client_secret=env.str('YTMUSIC_CLIENT_SECRET')),
        location=YTMUSIC_COUNTRY
    )
else:
    ytmusic = YTMusic(
        location=YTMUSIC_COUNTRY
    )


class YTMusic:
    def __init__(self, bot: 'NeonBot'):
        self.bot = bot

    async def search(self, keyword):
        results: list[dict] = await self.bot.loop.run_in_executor(
            self.bot.executor,
            functools.partial(ytmusic.search, keyword, limit=1, filter='songs'),
            []
        )
        result = results[0]

        return result.get('videoId')

    async def get_related_tracks(self, video_id: str) -> List[dict]:
        watch_playlist = await self.bot.loop.run_in_executor(
            self.bot.executor,
            functools.partial(ytmusic.get_watch_playlist, video_id),
            []
        )

        browser_id = watch_playlist['related']

        try:
            if not browser_id:
                raise YTMusicError('Browse id not found.')

            song_related = await self.bot.loop.run_in_executor(
                self.bot.executor,
                functools.partial(ytmusic.get_song_related, browser_id),
                []
            )
            tracks = song_related[0].get('contents', [])
        except (YTMusicError, IndexError):
            tracks = watch_playlist.get('tracks', [])

        related_tracks = []

        for track in tracks[1:]:
            if track.get('videoId'):
                related_tracks.append({'id': track.get('videoId'), 'title': track.get('title')})
            else:
                related_tracks.append({'id': track.get('counterpart')['videoId'], 'title': track.get('title')})

        return related_tracks

    async def get_random_song(self) -> List[dict]:
        homes = await self.bot.loop.run_in_executor(
            self.bot.executor,
            functools.partial(ytmusic.get_home),
            []
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

    async def like_song(self, video_id: str) -> None:
        try:
            await self.bot.loop.run_in_executor(
                self.bot.executor,
                functools.partial(ytmusic.rate_song, video_id, LikeStatus.LIKE),
                []
            )
        except Exception as error:
            log.debug(error, exc_info=True)
            log.error('Failed to like song. ' + str(error))

    async def get_account_info(self):
        return await self.bot.loop.run_in_executor(
            self.bot.executor,
            functools.partial(ytmusic.get_account_info),
            []
        )
