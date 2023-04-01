from enum import Enum


class PlayerState(Enum):
    NONE = -1
    STOPPED = 0
    PLAYING = 1
    JUMPED = 2
    PAUSED = 3
    AUTO_PAUSED = 4
    REMOVED = 5
