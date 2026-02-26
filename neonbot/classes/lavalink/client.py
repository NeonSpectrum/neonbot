from typing import TYPE_CHECKING
from typing import Union, Type

from lavalink import Client as LavalinkClient

from neonbot.classes.lavalink.player_manager import PlayerManager
from neonbot.classes.player.player import Player

if TYPE_CHECKING:
    from neonbot import NeonBot


class Client(LavalinkClient):
    def __init__(self, bot, user_id: Union[int, str], player: Type[Player] = Player, *args, **kwargs):
        super().__init__(user_id, player, *args, **kwargs)
        self.bot: 'NeonBot' = bot
        self.player_manager: PlayerManager = PlayerManager(self, player)
