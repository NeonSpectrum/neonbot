from typing import Dict, Optional

from pydantic import BaseModel


class PanelServer(BaseModel):
    channel_id: Optional[int] = None
    message_id: Optional[int] = None


class PanelModel(BaseModel):
    servers: Dict[str, PanelServer]
