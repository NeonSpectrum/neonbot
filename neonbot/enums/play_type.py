from enum import Enum


class PlayType(Enum):
    SEARCH = 1
    YOUTUBE = 2
    SPOTIFY = 3

    def __eq__(self, other):
        return self.value == other
