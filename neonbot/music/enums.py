from dataclasses import dataclass
from enum import Enum
from typing import Optional

import discord
from lavalink import AudioTrack


class MessageType(Enum):
    PLAYING = 1
    FINISHED = 2

    def __eq__(self, other):
        if isinstance(other, MessageType):
            return self is other
        return self.value == other

    def __hash__(self):
        return hash(self.value)


class Repeat(Enum):
    OFF = 0
    SINGLE = 1
    ALL = 2

    def __eq__(self, other):
        if isinstance(other, Repeat):
            return self is other
        return self.value == other

    def __hash__(self):
        return hash(self.value)


@dataclass
class PlayerMessage:
    type: MessageType
    track: AudioTrack
    compact: bool
    message: Optional[discord.Message] = None
