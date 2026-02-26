from enum import Enum


class MessageType(Enum):
    PLAYING = 1
    FINISHED = 2

    def __eq__(self, other):
        return self.value == other
