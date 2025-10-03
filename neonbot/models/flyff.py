from pydantic import BaseModel


class FlyffTimer(BaseModel):
    next_timer: int
    initial_interval: int
    interval: int

class FlyffModel(BaseModel):
    channel_id: int = None
    message_id: int = None
    world_start_time: int = None
    started: bool = False
    timers: Dict[str, FlyffTimer]
