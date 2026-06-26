import asyncio
from typing import TYPE_CHECKING

import discord
from i18n import t

from neonbot.discord_ui.embed import Embed
from neonbot.discord_ui.view import Button, View
from neonbot.music.enums import Repeat
from neonbot.utils import log

if TYPE_CHECKING:
    from neonbot import NeonBot


class PlayerControls:
    def __init__(self, bot: 'NeonBot', guild_id):
        self.bot = bot
        self.guild_id = guild_id
        self.view = None

    @property
    def player(self):
        return self.bot.get_player_instance(self.guild_id)

    def update_buttons(self, views):
        player = self.player
        if not player:
            return views

        if player.shuffle:
            views[0].style = discord.ButtonStyle.primary
        else:
            views[0].style = discord.ButtonStyle.secondary

        views[1].disabled = not (0 <= player.current_queue - 1 < len(player.playlist))

        if player.is_playing and not player.paused:
            views[2].emoji = '⏸️'
        else:
            views[2].emoji = '▶️'

        views[2].disabled = (
            not player.is_playing
            and not player.paused
            and player.loop == Repeat.OFF
            and not player.shuffle
            and not player.autoplay
        )

        views[3].disabled = (
            (not player.is_playing or player.is_last_track)
            and player.loop == Repeat.OFF
            and not player.autoplay
            and not player.shuffle
        )

        if player.loop == Repeat.OFF:
            views[4].emoji = '🔁'
            views[4].style = discord.ButtonStyle.secondary
        elif player.loop == Repeat.SINGLE:
            views[4].emoji = '🔂'
            views[4].style = discord.ButtonStyle.primary
        elif player.loop == Repeat.ALL:
            views[4].emoji = '🔁'
            views[4].style = discord.ButtonStyle.primary

        if player.autoplay:
            views[5].style = discord.ButtonStyle.primary
        else:
            views[5].style = discord.ButtonStyle.secondary

        return views

    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction['NeonBot']):
        player = self.player
        if not player:
            return

        try:
            if not interaction.response.is_done():
                await interaction.response.defer()

            async with player.command_lock:
                await self._handle_button(button, interaction, player)
        except Exception as e:
            log.exception(f'Guild {self.guild_id}: button callback error: {e}')
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=Embed(t('music.button_error')), ephemeral=True
                    )
            except Exception:
                pass

    async def _handle_button(self, button, interaction, player):
        async def send_message(message):
            await interaction.channel.send(embed=Embed(message))
            message = message.replace(interaction.user.mention, str(interaction.user))
            log.cmd(interaction, message)

        voice_client = player.ctx.voice_client if player.ctx else None
        if not interaction.user.voice or (
            interaction.user.voice and voice_client and interaction.user.voice.channel != voice_client.channel
        ):
            if not await self.bot.is_owner(interaction.user):
                await self.bot.send_response(interaction, embed=Embed(t('music.cannot_interact')), ephemeral=True)
                return

        tasks = []

        if button.emoji.name == '▶️':  # play
            if player.paused:
                tasks.append(player.resume(requester=interaction.user))
            else:
                tasks.append(player.play_next())
        elif button.emoji.name == '⏸️':  # pause
            tasks.append(player.pause(requester=interaction.user))
        elif button.emoji.name == '⏮️':  # prev
            tasks.append(send_message(t('music.player_controls_pressed', action='back', user=interaction.user.mention)))
            tasks.append(player.prev())
        elif button.emoji.name == '⏭️':  # next
            tasks.append(send_message(t('music.player_controls_pressed', action='next', user=interaction.user.mention)))
            tasks.append(player.next())
        elif button.emoji.name in ('🔁', '🔂'):  # repeat
            modes = [Repeat.OFF, Repeat.SINGLE, Repeat.ALL]
            index = (modes.index(Repeat(player.loop)) + 1) % 3
            mode = modes[index]

            tasks.append(send_message(t('music.repeat_changed', mode=mode.name.lower(), user=interaction.user.mention)))
            player.set_loop(mode.value)
        elif button.emoji.name == '🔀':  # shuffle
            state = not player.shuffle

            tasks.append(send_message(t('music.shuffle_changed', mode='on' if state else 'off', user=interaction.user.mention)))
            player.set_shuffle(state)
        elif button.emoji.name == '♾️':  # autoplay
            state = not player.autoplay

            tasks.append(send_message(t('music.autoplay_changed', mode='on' if state else 'off', user=interaction.user.mention)))
            player.set_autoplay(state)
        elif button.emoji.name == '⏏️':  # reset
            tasks.append(send_message(t('music.player_controls_pressed', action='reset', user=interaction.user.mention)))
            tasks.append(player.reset())

        await asyncio.gather(*tasks)

    def initialize(self) -> None:
        buttons = [
            Button(emoji='🔀'),
            Button(emoji='⏮️', style=discord.ButtonStyle.primary),
            Button(emoji='⏸️', style=discord.ButtonStyle.primary),
            Button(emoji='⏭️', style=discord.ButtonStyle.primary),
            Button(emoji='🔁'),
            Button(emoji='♾️', label=t('music.autoplay_label')),
            Button(emoji='⏏️', label=t('music.reset_label')),
        ]
        self.update_buttons(buttons)

        def callback(*args, **kwargs):
            self.bot.loop.create_task(self.callback(*args, **kwargs))

        self.view = View.create_button(buttons, callback, timeout=None)

    def get(self) -> View:
        self.refresh()

        return self.view

    def refresh(self) -> None:
        if not self.view:
            return

        views = self.view.children
        self.view.clear_items()

        for button in self.update_buttons(views):
            self.view.add_item(button)
