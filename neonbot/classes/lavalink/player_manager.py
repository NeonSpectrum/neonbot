from typing import Type

from lavalink.playermanager import PlayerManager as BasePlayerManager

from neonbot.classes.player.player import Player


class PlayerManager(BasePlayerManager):
    def __init__(self, client, player: Type['Player'] = Player):
        super().__init__(client, player)
