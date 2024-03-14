from typing import List, Optional, Dict

from pydantic import BaseModel, RootModel


class PteroServer(BaseModel):
    channel_id: int
    message_id: Optional[int] = None


class Ptero(BaseModel):
    servers: Dict[str, PteroServer]
