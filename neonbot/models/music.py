from typing import Optional

from pydantic import BaseModel


class Music(BaseModel):
    volume: int
    repeat: int
    shuffle: bool
    autoplay: bool
