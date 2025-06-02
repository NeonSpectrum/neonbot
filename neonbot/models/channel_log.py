from typing import Optional

from pydantic import BaseModel


class ChannelLogModel(BaseModel):
    connect: Optional[int] = None
    mute: Optional[int] = None
    deafen: Optional[int] = None
    server_deafen: Optional[int] = None
    server_mute: Optional[int] = None
    status: Optional[int] = None
    activity: Optional[int] = None
    stream: Optional[int] = None
    video: Optional[int] = None
