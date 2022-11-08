from __future__ import annotations

import functools
from concurrent.futures import ThreadPoolExecutor

import yt_dlp

from .ytdl_info import YtdlInfo
from .. import bot
from ..utils import log
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
                "ignoreerrors": False,
                "extract_flat": "in_playlist",
                "geo_bypass": True,
                "geo_bypass_country": "PH",
                "source_address": "0.0.0.0",
                "extractor_args": {'youtube': {'skip': ['dash', 'hls']}},
                "outtmpl": "./tmp/youtube_dl/%(id)s",
                **extra_params,
            }
        )

    async def extract_info(self, keyword: str, process: bool = False) -> YtdlInfo:
        try:
            result = await self.loop.run_in_executor(
                self.thread_pool,
                functools.partial(
                    self.ytdl.extract_info, keyword, download=False, process=process
                ),
            )

            return YtdlInfo(result)
        except yt_dlp.utils.YoutubeDLError as error:
            log.exception(error)
            raise YtdlError(
                "Video not available or rate limited due to many song requests. Try again later."
            )

    async def process_entry(self, info: dict) -> YtdlInfo:
        try:
            result = await self.loop.run_in_executor(
                self.thread_pool,
                functools.partial(self.ytdl.process_ie_result, info, download=True),
            )

            return YtdlInfo(result)
        except yt_dlp.utils.YoutubeDLError as error:
            log.exception(error)
            raise YtdlError(
                "Video not available or rate limited due to many song requests. Try again later."
            )

    @classmethod
    def create(cls, extra_params) -> Ytdl:
        return cls(extra_params)
