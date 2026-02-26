from dataclasses import dataclass
from typing import Optional

import discord
from lavalink import AudioTrack

from neonbot.enums import MessageType


@dataclass
class PlayerMessage:
    type: MessageType
    track: AudioTrack
    compact: bool
    message: Optional[discord.Message] = None
