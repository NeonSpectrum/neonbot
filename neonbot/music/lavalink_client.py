from typing import TYPE_CHECKING, Type, Union

from lavalink import Client as LavalinkClient
from lavalink.playermanager import PlayerManager as BasePlayerManager

from neonbot.music.player import Player

if TYPE_CHECKING:
    from neonbot import NeonBot


class PlayerManager(BasePlayerManager):
    def __init__(self, client, player: Type['Player'] = Player):
        super().__init__(client, player)


class Client(LavalinkClient):
    def __init__(self, bot, user_id: Union[int, str], player: Type[Player] = Player, *args, **kwargs):
        super().__init__(user_id, player, *args, **kwargs)
        self.bot: 'NeonBot' = bot
        self.player_manager: PlayerManager = PlayerManager(self, player)
