from typing import Dict

from pydantic import BaseModel


class FlyffTimer(BaseModel):
    initial_interval: int
    interval: int

class FlyffModel(BaseModel):
    status_channel_id: int = None
    status_message_id: int = None
    alert_channel_id: int = None
    world_start_time: str = None
    timers: Dict[str, FlyffTimer]
