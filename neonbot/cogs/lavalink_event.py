import asyncio
from typing import TYPE_CHECKING

from discord.ext import commands
from lavalink import (
    NodeConnectedEvent, NodeDisconnectedEvent, NodeReadyEvent,
    TrackEndEvent, TrackStartEvent, TrackExceptionEvent, TrackStuckEvent,
    listener
)
from i18n import t

from neonbot.discord_ui.embed import Embed
from neonbot.utils import log

if TYPE_CHECKING:
    from neonbot import NeonBot

RECONNECT_BASE_DELAY = 2
RECONNECT_MAX_DELAY = 60
RECONNECT_MAX_ATTEMPTS = 10


class LavalinkEvent(commands.Cog):
    def __init__(self, bot: 'NeonBot'):
        self.bot = bot
        self._reconnect_tasks = {}
        self.bot.lavalink.add_event_hooks(self)

    def cog_unload(self):
        for task in self._reconnect_tasks.values():
            task.cancel()
        self._reconnect_tasks.clear()
        # noinspection PyProtectedMember
        self.bot.lavalink._event_hooks.clear()

    @listener(NodeConnectedEvent)
    async def on_node_connected(self, event: NodeConnectedEvent):
        log.info(f'Node connected: {event.node.name}')

        for guild_id, player in self.bot.lavalink.player_manager.items():
            if player._reconnecting:
                player._reconnecting = False
                log.info(f'Guild {guild_id}: node reconnected, resuming playback')
                try:
                    if player.ctx:
                        await player.send_message(embed=Embed(t('music.node_reconnected')))
                    if player.last_track and len(player.track_list) > 0:
                        await player.play_next()
                except Exception as e:
                    log.error(f'Guild {guild_id}: failed to resume after reconnect: {e}')

    @listener(NodeDisconnectedEvent)
    async def on_node_disconnected(self, event: NodeDisconnectedEvent):
        log.warn(f'Node disconnected: {event.node.name}')

        for guild_id, player in self.bot.lavalink.player_manager.items():
            if hasattr(player, 'node') and player.node == event.node:
                player._reconnecting = True
                log.info(f'Guild {guild_id}: marked as reconnecting')
                try:
                    if player.ctx:
                        await player.send_message(embed=Embed(t('music.node_disconnected')))
                except Exception:
                    pass

        task = self._reconnect_tasks.get(event.node.name)
        if task and not task.done():
            task.cancel()
        self._reconnect_tasks[event.node.name] = self.bot.loop.create_task(
            self._reconnect_node(event.node)
        )

    async def _reconnect_node(self, node):
        delay = RECONNECT_BASE_DELAY
        for attempt in range(RECONNECT_MAX_ATTEMPTS):
            await asyncio.sleep(delay)
            try:
                await node.connect()
                log.info(f'Node {node.name}: reconnected on attempt {attempt + 1}')
                return
            except Exception as e:
                log.warn(f'Node {node.name}: reconnect attempt {attempt + 1} failed: {e}')
                delay = min(delay * 2, RECONNECT_MAX_DELAY)

        log.error(f'Node {node.name}: failed to reconnect after {RECONNECT_MAX_ATTEMPTS} attempts')
        for guild_id, player in self.bot.lavalink.player_manager.items():
            if player._reconnecting:
                player._reconnecting = False
                try:
                    if player.ctx:
                        await player.send_message(embed=Embed(t('music.node_reconnect_failed')))
                except Exception:
                    pass

    @listener(NodeReadyEvent)
    async def on_node_ready(self, event: NodeReadyEvent):
        log.info(f'Node ready: {event.node.name}')

    @listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent):
        log.debug(f'TrackStartEvent: {event.track}')

        if event.track is None:
            log.warn('event.track is missing.')
            return

        player = self.bot.get_player_instance(event.player.guild_id)
        if not player:
            return

        await player.track_start_event(event)

    @listener(TrackEndEvent)
    async def on_track_end(self, event: TrackEndEvent):
        log.debug(f'TrackEndEvent: {event.track} Reason: {event.reason}')

        player = self.bot.get_player_instance(event.player.guild_id)
        if not player:
            return

        if event.track is None:
            log.warn(f'event.track is missing. overwriting with {player.last_track}')
            # noinspection PyFinal
            event.track = player.last_track

            if event.track is None:
                log.warn('event.track is still missing. skipping event.')
                return

        await player.track_end_event(event)

    @listener(TrackExceptionEvent)
    async def on_track_exception(self, event: TrackExceptionEvent):
        log.error(f'TrackExceptionEvent: {event.track} - {event.message}')

        player = self.bot.get_player_instance(event.player.guild_id)
        if not player:
            return

        try:
            if player.ctx:
                await player.send_message(embed=Embed(t('music.track_failed', error=event.message)))
        except Exception:
            pass

        try:
            await player.skip()
        except Exception as e:
            log.error(f'Guild {player.guild_id}: failed to skip after exception: {e}')

    @listener(TrackStuckEvent)
    async def on_track_stuck(self, event: TrackStuckEvent):
        log.warn(f'TrackStuckEvent: {event.track} (threshold: {event.threshold}ms)')

        player = self.bot.get_player_instance(event.player.guild_id)
        if not player:
            return

        try:
            await player.skip()
        except Exception as e:
            log.error(f'Guild {player.guild_id}: failed to skip stuck track: {e}')


async def setup(bot: 'NeonBot') -> None:
    await bot.add_cog(LavalinkEvent(bot))
