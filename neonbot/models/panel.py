from typing import List, Optional, Dict

from pydantic import BaseModel, RootModel


class PanelServer(BaseModel):
    channel_id: Optional[int] = None
    message_id: Optional[int] = None


class Panel(BaseModel):
    servers: Dict[str, PanelServer]
