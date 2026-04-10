from typing import Optional

from pydantic import BaseModel


class MusicModel(BaseModel):
    volume: int
    repeat: int
    shuffle: bool
    autoplay: bool
    channel_id: Optional[int] = None
    autojoin_channel_id: Optional[int] = None
