from __future__ import annotations

import asyncio
import datetime
import functools
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import yt_dlp
from envparse import env

from .. import bot
from ..utils import log
from ..utils.constants import YOUTUBE_CACHE_DIR, YOUTUBE_DOWNLOADS_DIR
from ..utils.exceptions import YtdlError
from .ytdl_info import YtdlInfo


class Ytdl:
    def __init__(self, extra_params=None) -> None:
        if extra_params is None:
            extra_params = {}
        self.loop = bot.loop
        self.ytdl_opts = {
            'default_search': 'ytsearch1',
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            # "geo_bypass": True,
            # "geo_bypass_country": "PH",
            'source_address': '0.0.0.0',
            # 'outtmpl': YOUTUBE_DOWNLOADS_DIR + '/%(id)s',
            'skip_download': True,
            'cachedir': YOUTUBE_CACHE_DIR,
            'compat_opts': {'no-youtube-unavailable-videos': True},
            'cookiefile': env.str('YTDL_COOKIES', default=None),
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
                            functools.partial(ytdl.extract_info, keyword, download),
                        )

                    return YtdlInfo(result)
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

    @staticmethod
    def is_expired(stream_url: str) -> bool:
        parsed_url = urllib.parse.urlparse(stream_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if 'expire' in query_params:
            expiry_timestamp = int(query_params['expire'][0])

            expiry_datetime = datetime.datetime.fromtimestamp(expiry_timestamp)
            current_datetime = datetime.datetime.now()

            return current_datetime >= expiry_datetime

        return False

    @staticmethod
    def prepare_filename(*args, **kwargs):
        return Ytdl().ytdl.prepare_filename(*args, **kwargs)

    @classmethod
    def create(cls, extra_params) -> Ytdl:
        return cls(extra_params)
