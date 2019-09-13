import functools
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import youtube_dl
from addict import Dict

from .. import bot, env
from ..helpers.date import date


class Ytdl:
    def __init__(self, extra_params={}):
        self.thread_pool = ThreadPoolExecutor(max_workers=3)
        self.loop = bot.loop
        self.ytdl = youtube_dl.YoutubeDL(
            {
                "default_search": "ytsearch5",
                "format": "95/bestaudio",
                "quiet": True,
                "nocheckcertificate": True,
                "ignoreerrors": True,
                "source_address": "0.0.0.0",
                "extract_flat": "in_playlist",
                **extra_params,
            }
        )

    async def extract_info(self, *args, **kwargs):
        result = await self.loop.run_in_executor(
            self.thread_pool,
            functools.partial(self.ytdl.extract_info, *args, download=False, **kwargs),
        )
        info = Dict(result)
        return info.get("entries", info)

    async def process_entry(self, info):
        result = await self.loop.run_in_executor(
            self.thread_pool,
            functools.partial(self.ytdl.process_ie_result, info, download=False),
        )
        return Dict(result)

    def parse_choices(self, info):
        return [
            Dict(
                id=entry.id,
                title=entry.get("title", "*Not Available*"),
                url=f"https://www.youtube.com/watch?v={entry.id}",
            )
            for entry in info
        ]

    def parse_info(self, info):
        def parse_description(description):
            description_arr = description.split("\n")[:15]
            while len("\n".join(description_arr)) > 1000:
                description_arr.pop()
            if len(description.split("\n")) != len(description_arr):
                description_arr.append("...")
            return "\n".join(description_arr)

        def parse_entry(entry):
            return Dict(
                id=entry.id,
                title=entry.title,
                description=parse_description(entry.description),
                uploader=entry.uploader,
                duration=entry.duration,
                thumbnail=entry.thumbnail,
                stream=entry.url,
                url=entry.webpage_url,
                view_count=f"{entry.view_count:,}",
                upload_date=datetime.strptime(entry.upload_date, "%Y%m%d").strftime(
                    "%b %d, %Y"
                ),
            )

        if isinstance(info, list):
            return [parse_entry(entry) for entry in info if entry]

        return parse_entry(info) if info else None

    @staticmethod
    async def get_related_videos(video_id):
        res = await bot.session.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "relatedToVideoId": video_id,
                "type": "video",
                "key": env("GOOGLE_API"),
            },
        )
        json = await res.json()
        return Dict(json)["items"]

    @staticmethod
    def is_link_expired(url):
        params = Dict(parse_qs(urlparse(url).query))
        return date().timestamp() > int(params.expire[0]) - 1800 if params else False
