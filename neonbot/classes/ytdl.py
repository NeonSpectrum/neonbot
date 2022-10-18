from __future__ import annotations

import functools
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Union

import yt_dlp

from .. import bot
from ..utils.date import format_seconds
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

    async def extract_info(self, keyword: str, process: bool = False) -> Union[List[dict], dict]:
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

        result = result.get("entries", result)

        if isinstance(result, dict):
            result = self.format_simple_result(result) if result else None
        else:
            result = [self.format_simple_result(entry) for entry in result if entry]

        if self.is_single_search:
            return result[0] if len(result) > 0 else None

        return result

    async def process_entry(self, info: dict) -> dict:
        result = await self.loop.run_in_executor(
            self.thread_pool,
            functools.partial(self.ytdl.process_ie_result, info, download=True),
        )
        if not result:
            raise YtdlError(
                "Video not available or rate limited due to many song requests. Try again later."
            )

        return result

    def parse_choices(self, info: dict) -> list:
        return [self.format_simple_result(entry) for entry in info]

    def parse_info(self, info: dict) -> Union[List[dict], dict]:
        if isinstance(info, list):
            return [self.format_detailed_result(entry) for entry in info if entry]

        return self.format_detailed_result(info) if info else None

    def format_description(self, description: str) -> str:
        description_arr = description.split("\n")[:15]
        while len("\n".join(description_arr)) > 1000:
            description_arr.pop()
        if len(description.split("\n")) != len(description_arr):
            description_arr.append("...")
        return "\n".join(description_arr)

    def format_simple_result(self, entry: dict) -> dict:
        return dict(
            _type='url',
            ie_key='Youtube',
            id=entry.get('id'),
            title=entry.get("title", "*Not Available*"),
            duration=entry.get("duration"),
            url='https://www.youtube.com/watch?v=' + entry.get('id')
        )

    def format_detailed_result(self, entry: dict) -> dict:
        return dict(
            id=entry.get('id'),
            title=entry.get('title'),
            description=self.format_description(entry.get('description')),
            uploader=entry.get('uploader'),
            duration=entry.get('duration'),
            formatted_duration=format_seconds(entry.get('duration')) if entry.get('duration') else "N/A",
            thumbnail=entry.get('thumbnail'),
            stream=entry.get('url') if entry.get('is_live') else f"./tmp/youtube_dl/{entry.get('id')}",
            url=entry.get('webpage_url'),
            is_live=entry.get('is_live'),
            view_count=f"{entry.get('view_count'):,}",
            upload_date=datetime.strptime(entry.get('upload_date'), "%Y%m%d").strftime(
                "%b %d, %Y"
            ),
        )

    @classmethod
    def create(cls, extra_params) -> Ytdl:
        return cls(extra_params)


ytdl = Ytdl()
