from typing import Optional

from pydantic import BaseModel


class Channel(BaseModel):
    voice_log: Optional[int]
    presence_log: Optional[int]
    msgdelete_log: Optional[int]
