from typing import Optional

from pydantic import BaseModel


class ChannelLog(BaseModel):
    connect: Optional[int] = None
    mute: Optional[int] = None
    deafen: Optional[int] = None
    server_deafen: Optional[int] = None
    server_mute: Optional[int] = None
    status: Optional[int] = None
    activity: Optional[int] = None
