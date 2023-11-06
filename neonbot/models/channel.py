from typing import Optional

from pydantic import BaseModel


class Channel(BaseModel):
    voice_log: Optional[int] = None
    presence_log: Optional[int] = None
    msgdelete_log: Optional[int] = None
    chatgpt: Optional[int] = None
