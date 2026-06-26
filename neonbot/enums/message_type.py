from enum import Enum


class MessageType(Enum):
    PLAYING = 1
    FINISHED = 2

    def __eq__(self, other):
        if isinstance(other, MessageType):
            return self is other
        return self.value == other
