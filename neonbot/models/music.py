from typing import Optional

from pydantic import BaseModel


class MusicModel(BaseModel):
    volume: int
    repeat: int
    shuffle: bool
    autoplay: bool
    autojoin_channel_id: Optional[int] = None
