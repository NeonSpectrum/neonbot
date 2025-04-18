from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor

from envparse import env
import yt_dlp

from .ytdl_info import YtdlInfo
from .. import bot
from ..utils import log
from ..utils.constants import YOUTUBE_DOWNLOADS_DIR, YOUTUBE_CACHE_DIR
from ..utils.exceptions import YtdlError


class Ytdl:
    def __init__(self, extra_params=None) -> None:
        if extra_params is None:
            extra_params = {}
        self.loop = bot.loop
        self.ytdl_opts = {
            "default_search": "ytsearch5",
            "format": "bestaudio/best",
            "quiet": True,
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
            "cookiefile": env.str("YTDL_COOKIES", default=None),
            "external_downloader": "aria2c",
            **extra_params,
        }

    async def extract_info(self, keyword: str, download: bool = False) -> YtdlInfo:
        tries = 0
        max_retries = 5

        with yt_dlp.YoutubeDL(self.ytdl_opts) as ytdl:
            while tries <= max_retries:
                try:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        result = await self.loop.run_in_executor(
                            executor,
                            functools.partial(
                                ytdl.extract_info, keyword, download, process=True
                            ),
                        )

                    return YtdlInfo(self, result)
                except yt_dlp.utils.DownloadError as error:
                    if 'Sign in' in str(error):
                        raise YtdlError(error)

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

        with yt_dlp.YoutubeDL(self.ytdl_opts) as ytdl:
            while tries <= max_retries:
                try:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        result = await self.loop.run_in_executor(
                            executor,
                            functools.partial(ytdl.process_ie_result, info, download=not info.get('is_live')),
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

    @classmethod
    def create(cls, extra_params) -> Ytdl:
        return cls(extra_params)
