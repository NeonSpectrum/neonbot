from __future__ import annotations

import functools
from concurrent.futures import ThreadPoolExecutor

import yt_dlp

from .ytdl_info import YtdlInfo
from .. import bot
from ..utils.exceptions import YtdlError


class Ytdl:
    def __init__(self, extra_params=None) -> None:
        if extra_params is None:
            extra_params = {}
        self.thread_pool = ThreadPoolExecutor()
        self.loop = bot.loop
        self.ytdl = yt_dlp.YoutubeDL(
            {
                "default_search": "ytsearch5",
                "format": "95/bestaudio/best/worst",
                "quiet": True,
                "nocheckcertificate": True,
                "ignoreerrors": True,
                "extract_flat": "in_playlist",
                "geo_bypass": True,
                "geo_bypass_country": "PH",
                "source_address": "0.0.0.0",
                "extractor_args": {'youtube': {'skip': ['dash', 'hls']}},
                "outtmpl": "./tmp/youtube_dl/%(id)s",
                **extra_params,
            }
        )
        self.is_single_search = self.ytdl.params.get('default_search') == 'ytsearch1'

    async def extract_info(self, keyword: str, process: bool = False) -> YtdlInfo:
        result = await self.loop.run_in_executor(
            self.thread_pool,
            functools.partial(
                self.ytdl.extract_info, keyword, download=False, process=process
            ),
        )

        if not result:
            raise YtdlError(
                "Video not available or rate limited due to many song requests. Try again later."
            )

        return YtdlInfo(result)

    async def process_entry(self, info: dict) -> YtdlInfo:
        result = await self.loop.run_in_executor(
            self.thread_pool,
            functools.partial(self.ytdl.process_ie_result, info, download=True),
        )
        if not result:
            raise YtdlError(
                "Video not available or rate limited due to many song requests. Try again later."
            )

        return YtdlInfo(result)

    @classmethod
    def create(cls, extra_params) -> Ytdl:
        return cls(extra_params)


ytdl = Ytdl()
