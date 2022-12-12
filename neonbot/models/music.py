from pydantic import BaseModel


class Music(BaseModel):
    volume: int
    repeat: int
    shuffle: bool
