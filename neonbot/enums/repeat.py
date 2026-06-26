from enum import Enum


class Repeat(Enum):
    OFF = 0
    SINGLE = 1
    ALL = 2

    def __eq__(self, other):
        if isinstance(other, Repeat):
            return self is other
        return self.value == other
