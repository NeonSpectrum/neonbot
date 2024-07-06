from __future__ import annotations

import functools
from concurrent.futures import ThreadPoolExecutor

import yt_dlp

from .ytdl_info import YtdlInfo
from .. import bot
from ..utils.constants import YOUTUBE_TMP_DIR
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
                "format": "bestaudio/best",
                "quiet": True,
                "nocheckcertificate": True,
                "ignoreerrors": False,
                "extract_flat": "in_playlist",
                # "geo_bypass": True,
                # "geo_bypass_country": "PH",
                # "source_address": "0.0.0.0",
                "outtmpl": YOUTUBE_TMP_DIR + "/%(id)s",
                "compat_opts": {
                    "no-youtube-unavailable-videos": True
                },
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                **extra_params,
            }
        )

    async def extract_info(self, keyword: str) -> YtdlInfo:
        try:
            result = await self.loop.run_in_executor(
                self.thread_pool,
                functools.partial(
                    self.ytdl.extract_info, keyword, download=False, process=True
                ),
            )

            return YtdlInfo(result)
        except yt_dlp.utils.YoutubeDLError as error:
            raise YtdlError(error)

    async def process_entry(self, info: dict) -> YtdlInfo:
        try:
            result = await self.loop.run_in_executor(
                self.thread_pool,
                functools.partial(self.ytdl.process_ie_result, info, download=not info.get('is_live')),
            )

            return YtdlInfo(result)
        except yt_dlp.utils.YoutubeDLError as error:
            raise YtdlError(error)

    @classmethod
    def create(cls, extra_params) -> Ytdl:
        return cls(extra_params)
