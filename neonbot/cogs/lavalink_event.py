from typing import TYPE_CHECKING

from discord.ext import commands
from lavalink import NodeConnectedEvent, NodeDisconnectedEvent, NodeReadyEvent, TrackEndEvent, TrackStartEvent, listener

from neonbot.utils import log

if TYPE_CHECKING:
    from neonbot import NeonBot


class LavalinkEvent(commands.Cog):
    def __init__(self, bot: 'NeonBot'):
        self.bot = bot
        self.bot.lavalink.add_event_hooks(self)

    def cog_unload(self):
        # noinspection PyProtectedMember
        self.bot.lavalink._event_hooks.clear()

    @listener(NodeConnectedEvent)
    async def on_node_connected(self, *args):
        log.info('Node connected.')

    @listener(NodeDisconnectedEvent)
    async def on_node_disconnected(self, *args):
        log.info('Node disconnected.')

    @listener(NodeReadyEvent)
    async def on_node_ready(self, *args):
        log.info('Node ready.')

    @listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent):
        log.debug(f'TrackStartEvent: {event.track}')

        if event.track is None:
            log.warn('event.track is missing.')
            return

        player = self.bot.get_player_instance(event.player.guild_id)

        if player:
            await player.track_start_event(event)

    @listener(TrackEndEvent)
    async def on_track_end(self, event: TrackEndEvent):
        log.debug(f'TrackEndEvent: {event.track} Reason: {event.reason}')

        player = self.bot.get_player_instance(event.player.guild_id)

        if event.track is None:
            log.warn(f'event.track is missing. overwriting with {player.last_track}')
            # noinspection PyFinal
            event.track = player.last_track

            if event.track is None:
                log.warn(f'event.track is still missing. skipping event.')
                return

        if player:
            await player.track_end_event(event)


async def setup(bot: 'NeonBot') -> None:
    await bot.add_cog(LavalinkEvent(bot))
