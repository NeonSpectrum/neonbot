from typing import cast

from discord.ext import commands
from lavalink import listener, TrackEndEvent, TrackStartEvent, TrackExceptionEvent, NodeDisconnectedEvent, \
    NodeConnectedEvent, NodeReadyEvent

from neonbot import bot
from neonbot.classes.player import Player
from neonbot.utils import log


class LavalinkEvent(commands.Cog):
    def __init__(self):
        bot.lavalink.add_event_hooks(self)

    def cog_unload(self):
        # noinspection PyProtectedMember
        bot.lavalink._event_hooks.clear()

    @listener(NodeConnectedEvent)
    async def on_node_connected(self):
        log.info('Node connected.')

    @listener(NodeDisconnectedEvent)
    async def on_node_disconnected(self):
        log.info('Node disconnected.')

    @listener(NodeReadyEvent)
    async def on_node_disconnected(self):
        log.info('Node ready.')

    @listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent):
        player = cast(Player, event.player)
        await player.track_start_event(event)

    @listener(TrackExceptionEvent)
    async def on_track_end(self, event: TrackEndEvent):
        player = cast(Player, event.player)
        await player.track_end_event(event)


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LavalinkEvent())
