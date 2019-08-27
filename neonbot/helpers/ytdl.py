from urllib.parse import parse_qs, urlparse

import requests
import youtube_dl
from addict import Dict

from bot import env

from .constants import TIMEZONE
from .utils import date


class YTDLExtractor:
  info = Dict()

  def __init__(self, extra_params={}):
    self.ytdl = youtube_dl.YoutubeDL({
      "default_search": "ytsearch5",
      "format": "95/bestaudio",
      "quiet": True,
      "nocheckcertificate": True,
      "ignoreerrors": True,
      "logtostderr": False,
      "source_address": "0.0.0.0",
      **extra_params
    })

  def extract_info(self, *args, **kwargs):
    info = Dict(self.ytdl.extract_info(*args, download=False, **kwargs))
    self.info = info.get("entries", [info])
    return self

  def get_choices(self):
    return [
      Dict({
        "id": entry.id,
        "title": entry.get("title", "*Not Available*"),
        "url": "https://www.youtube.com/watch?v=" + entry.id
      }) for entry in self.info
    ]

  def get_list(self):
    return [
      Dict({
        "id": entry.id,
        "title": entry.title,
        "description": entry.description,
        "duration": entry.duration,
        "thumbnail": entry.thumbnail,
        "stream": entry.url,
        "url": entry.webpage_url
      }) for entry in self.info if entry
    ]


def get_related_videos(video_id):
  res = requests.get("https://www.googleapis.com/youtube/v3/search",
                     params={
                       "part": "snippet",
                       "relatedToVideoId": video_id,
                       "type": "video",
                       "key": env("GOOGLE_API")
                     })

  return Dict(res.json())["items"]


def is_link_expired(url):
  params = Dict(parse_qs(urlparse(url).query))
  if params:
    return date().timestamp() > int(params.expire[0]) - 1800
  return False
