from __future__ import annotations

import functools
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, List, Union
from urllib.parse import parse_qs, urlparse

import youtube_dl
from addict import Dict
from bs4 import BeautifulSoup

from .. import bot, env
from ..helpers.date import date
from ..helpers.exceptions import YtdlError


class Ytdl:
    def __init__(self, extra_params: dict = {}) -> None:
        self.thread_pool = ThreadPoolExecutor(max_workers=3)
        self.loop = bot.loop
        self.session = bot.session
        self.ytdl = youtube_dl.YoutubeDL(
            {
                "default_search": "ytsearch5",
                "format": "95/bestaudio",
                "quiet": True,
                "nocheckcertificate": True,
                "ignoreerrors": True,
                "extract_flat": "in_playlist",
                "geo_bypass": True,
                "geo_bypass_country": "PH",
                "source_address": "0.0.0.0",
                "youtube_include_dash_manifest": False,
                "outtmpl": "./tmp/youtube_dl/%(id)s",
                **extra_params,
            }
        )

    async def extract_info(self, *args: Any, **kwargs: Any) -> Union[list, Dict]:
        async def fetch(download: bool):
            return await self.loop.run_in_executor(
                self.thread_pool,
                functools.partial(self.ytdl.extract_info, *args, download=download, **kwargs),
            )

        result = await fetch(download=False)

        if not result:
            raise YtdlError(
                "Video not available or rate limited due to many song requests. Try again later."
            )

        if result.get("is_live") is None:
            result = await fetch(download=True)

        info = Dict(result)

        return info.get("entries", info)

    async def process_entry(self, info: Dict) -> Dict:
        result = await self.loop.run_in_executor(
            self.thread_pool,
            functools.partial(self.ytdl.process_ie_result, info, download=True),
        )
        if not result:
            raise YtdlError(
                "Video not available or rate limited due to many song requests. Try again later."
            )

        return Dict(result)

    def parse_choices(self, info: Dict) -> list:
        return [
            Dict(
                id=entry.id,
                title=entry.get("title", "*Not Available*"),
                url=f"https://www.youtube.com/watch?v={entry.id}",
            )
            for entry in info
        ]

    def parse_info(self, info: Dict) -> Union[List[Dict], Dict]:
        def parse_description(description: str) -> str:
            description_arr = description.split("\n")[:15]
            while len("\n".join(description_arr)) > 1000:
                description_arr.pop()
            if len(description.split("\n")) != len(description_arr):
                description_arr.append("...")
            return "\n".join(description_arr)

        def parse_entry(entry: Dict) -> Dict:
            return Dict(
                id=entry.id,
                title=entry.title,
                description=parse_description(entry.description),
                uploader=entry.uploader,
                duration=entry.duration,
                thumbnail=entry.thumbnail,
                stream=entry.url if entry.is_live else f"./tmp/youtube_dl/{entry.id}",
                url=entry.webpage_url,
                is_live=entry.is_live,
                view_count=f"{entry.view_count:,}",
                upload_date=datetime.strptime(entry.upload_date, "%Y%m%d").strftime(
                    "%b %d, %Y"
                ),
            )

        if isinstance(info, list):
            return [parse_entry(entry) for entry in info if entry]

        return parse_entry(info) if info else None

    @classmethod
    def create(cls, extra_params: dict) -> Ytdl:
        return cls(extra_params)

    def is_link_expired(self, url: str) -> bool:
        params = Dict(parse_qs(urlparse(url).query))
        return date().timestamp() > int(params.expire[0]) - 1800 if params else False
