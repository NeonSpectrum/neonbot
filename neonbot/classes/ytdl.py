from __future__ import annotations

import asyncio
import functools
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Coroutine, Optional, List

import yt_dlp
from envparse import env

from .ytdl_info import YtdlInfo
from .. import bot
from ..utils import log
from ..utils.constants import YOUTUBE_DOWNLOADS_DIR, YOUTUBE_CACHE_DIR
from ..utils.exceptions import YtdlError, ApiError


class Ytdl:
    def __init__(self, extra_params=None) -> None:
        if extra_params is None:
            extra_params = {}
        self.thread_pool = ThreadPoolExecutor()
        self.loop = bot.loop
        self.ytdl = yt_dlp.YoutubeDL(
            {
                "default_search": "ytsearch5",
                "format": "bestaudio/best",
                "quiet": os.path.isfile(YOUTUBE_CACHE_DIR + "/youtube-oauth2/token_data.json"),
                "no_warnings": True,
                "nocheckcertificate": True,
                "ignoreerrors": False,
                "extract_flat": "in_playlist",
                # "geo_bypass": True,
                # "geo_bypass_country": "PH",
                # "source_address": "0.0.0.0",
                "outtmpl": YOUTUBE_DOWNLOADS_DIR + "/%(id)s",
                "cachedir": YOUTUBE_CACHE_DIR,
                "compat_opts": {
                    "no-youtube-unavailable-videos": True
                },
                "username": "oauth2",
                "password": "",
                **extra_params,
            }
        )

    async def extract_info(self, keyword: str, download: bool = False) -> YtdlInfo:
        tries = 0
        max_retries = 5

        while tries <= max_retries:
            try:
                result = await self.loop.run_in_executor(
                    self.thread_pool,
                    functools.partial(
                        self.ytdl.extract_info, keyword, download, process=True
                    ),
                )

                return YtdlInfo(self, result)
            except yt_dlp.utils.DownloadError as error:
                tries += 1
                log.warn(f'Download failed. Retrying...[{tries}]')
                if tries > max_retries:
                    raise YtdlError(error)
                await asyncio.sleep(1)
            except yt_dlp.utils.YoutubeDLError as error:
                raise YtdlError(error)
            except:
                raise YtdlError()

    async def process_entry(self, info: dict) -> YtdlInfo:
        tries = 0
        max_retries = 5

        while tries <= max_retries:
            try:
                result = await self.loop.run_in_executor(
                    self.thread_pool,
                    functools.partial(self.ytdl.process_ie_result, info, download=not info.get('is_live')),
                )
                return YtdlInfo(self, result)
            except yt_dlp.utils.DownloadError as error:
                tries += 1
                log.warn(f'Download failed. Retrying...[{tries}]')
                if tries > max_retries:
                    raise YtdlError(error)
                await asyncio.sleep(1)
            except yt_dlp.utils.YoutubeDLError as error:
                raise YtdlError(error)

    @staticmethod
    def prepare_filename(*args, **kwargs):
        return Ytdl().ytdl.prepare_filename(*args, **kwargs)

    @staticmethod
    async def get_related_video(video_id: int, *, playlist: Optional[List[int]] = None) -> Optional[int]:
        res = await bot.session.get(
            'https://youtube-v31.p.rapidapi.com/search',
            params={
                'relatedToVideoId': str(video_id),
                'part': 'id,snippet',
                'type': 'video',
                'maxResults': 10
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-rapidapi-host": "youtube-v31.p.rapidapi.com",
                "x-rapidapi-key": env.str('RAPID_API_KEY')
            }
        )

        if res.status == 429:
            raise ApiError('Quota Exceeded')

        if res.status != 200:
            raise ApiError('Autoplay error: ' + await res.text())

        data = await res.json()

        if 'items' in data and len(data['items']) <= 1:
            raise ApiError('Track not found')

        for track in data['items'][1:]:
            if 'videoId' not in track['id'] or track['snippet']['liveBroadcastContent'] != 'none':
                continue

            track_id = track['id']['videoId']

            if playlist and track_id in playlist:
                continue

            return track_id

        raise ApiError('Track not found')

    @classmethod
    def create(cls, extra_params) -> Ytdl:
        return cls(extra_params)
