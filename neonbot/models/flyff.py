from typing import Dict, Optional

from pydantic import BaseModel


class FlyffTimer(BaseModel):
    initial_interval: int
    interval: int
    current_interval: Optional[int] = 0

class FlyffModel(BaseModel):
    status_channel_id: Optional[int] = None
    status_message_id: Optional[int] = None
    alert_channel_id: Optional[int] = None
    world_start_time: Optional[str] = None
    timers: Dict[str, FlyffTimer]
