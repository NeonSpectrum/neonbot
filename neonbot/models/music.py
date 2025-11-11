from pydantic import BaseModel


class MusicModel(BaseModel):
    volume: int
    repeat: int
    shuffle: bool
    autoplay: bool
