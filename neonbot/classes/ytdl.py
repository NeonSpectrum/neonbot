from __future__ import annotations

import functools
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, List, Union

import yt_dlp

from ..helpers.exceptions import YtdlError


class Ytdl:
    def __init__(self, bot, extra_params: dict = {}) -> None:
        self.thread_pool = ThreadPoolExecutor()
        self.loop = bot.loop
        self.session = bot.session
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
                # "youtube_include_dash_manifest": False,
                "outtmpl": "./tmp/youtube_dl/%(id)s",
                **extra_params,
            }
        )
        self.is_single_search = self.ytdl.params.get('default_search') == 'ytsearch1'

    async def extract_info(self, *args: Any, **kwargs: Any) -> Union[list, dict]:
        result = await self.loop.run_in_executor(
            self.thread_pool,
            functools.partial(
                self.ytdl.extract_info, *args, download=False, process=False, **kwargs
            ),
        )

        if not result:
            raise YtdlError(
                "Video not available or rate limited due to many song requests. Try again later."
            )

        result = await self.process_entry(result, download=not result.get("is_live"))
        result = result.get("entries", result)

        if self.is_single_search:
            return result[0] if len(result) > 0 else None

        return result

    async def process_entry(self, info: dict, download: bool = True) -> dict:
        result = await self.loop.run_in_executor(
            self.thread_pool,
            functools.partial(self.ytdl.process_ie_result, info, download=download),
        )
        if not result:
            raise YtdlError(
                "Video not available or rate limited due to many song requests. Try again later."
            )

        return result

    def parse_choices(self, info: dict) -> list:
        return [
            dict(
                id=entry.get('id'),
                title=entry.get("title", "*Not Available*"),
                url=f"https://www.youtube.com/watch?v={entry.get('id')}",
            )
            for entry in info
        ]

    def parse_info(self, info: dict) -> Union[List[dict], dict]:
        def format_description(description: str) -> str:
            description_arr = description.split("\n")[:15]
            while len("\n".join(description_arr)) > 1000:
                description_arr.pop()
            if len(description.split("\n")) != len(description_arr):
                description_arr.append("...")
            return "\n".join(description_arr)

        def parse_entry(entry: dict) -> dict:
            return dict(
                id=entry.get('id'),
                title=entry.get('title'),
                description=format_description(entry.get('description')),
                uploader=entry.get('uploader'),
                duration=entry.get('duration'),
                thumbnail=entry.get('thumbnail'),
                stream=entry.get('url') if entry.get('is_live') else f"./tmp/youtube_dl/{entry.get('id')}",
                # stream=entry.get('url'),
                url=entry.get('webpage_url'),
                is_live=entry.get('is_live'),
                view_count=f"{entry.get('view_count'):,}",
                upload_date=datetime.strptime(entry.get('upload_date'), "%Y%m%d").strftime(
                    "%b %d, %Y"
                ),
            )

        if isinstance(info, list):
            return [parse_entry(entry) for entry in info if entry]

        return parse_entry(info) if info else None

    @classmethod
    def create(cls, bot, extra_params) -> Ytdl:
        return cls(bot, extra_params)
