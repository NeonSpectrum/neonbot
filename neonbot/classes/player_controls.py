from typing import TYPE_CHECKING

import discord
from i18n import t

from neonbot import bot
from neonbot.classes.embed import Embed
from neonbot.classes.view import Button, View
from neonbot.enums import Repeat
from neonbot.utils import log

if TYPE_CHECKING:
    from neonbot.classes.player import Player


class PlayerControls:
    def __init__(self, player):
        self.player: Player = player
        self.view = None

    def update_buttons(self, views):
        # ["🔀","⏮️","⏸️","⏭️","🔁"]

        if self.player.shuffle:
            views[0].style = discord.ButtonStyle.primary
        else:
            views[0].style = discord.ButtonStyle.secondary

        views[1].disabled = not (0 <= self.player.current_queue - 1 < len(self.player.track_list))

        if not self.player.paused:
            views[2].emoji = '⏸️'
        else:
            views[2].emoji = '▶️'

        views[3].disabled = (
            self.player.is_last_track
            and self.player.loop == Repeat.OFF
            and not self.player.autoplay
            and not self.player.shuffle
        )

        if self.player.loop == Repeat.OFF:
            views[4].emoji = '🔁'
            views[4].style = discord.ButtonStyle.secondary
        elif self.player.loop == Repeat.SINGLE:
            views[4].emoji = '🔂'
            views[4].style = discord.ButtonStyle.primary
        elif self.player.loop == Repeat.ALL:
            views[4].emoji = '🔁'
            views[4].style = discord.ButtonStyle.primary

        if self.player.autoplay:
            views[5].style = discord.ButtonStyle.primary
        else:
            views[5].style = discord.ButtonStyle.secondary

        return views

    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        async def send_message(message):
            await interaction.channel.send(embed=Embed(message))
            log.cmd(interaction, message)

        if not interaction.user.voice or (
            interaction.user.voice and interaction.user.voice.channel != self.player.ctx.voice_client.channel
        ):
            if not await bot.is_owner(interaction.user):
                await bot.send_response(interaction, embed=Embed(t('music.cannot_interact')), ephemeral=True)
                return

        if button.emoji.name == '▶️':  # play
            if self.player.paused:
                await self.player.resume(requester=interaction.user)
            else:
                await self.player.play()
        elif button.emoji.name == '⏸️':  # pause
            await self.player.pause(requester=interaction.user)
        elif button.emoji.name == '⏮️':  # prev
            bot.loop.create_task(
                send_message(t('music.player_controls_pressed', action='back', user=interaction.user.mention))
            )

            await self.player.prev()
        elif button.emoji.name == '⏭️':  # next
            bot.loop.create_task(
                send_message(t('music.player_controls_pressed', action='next', user=interaction.user.mention))
            )

            await self.player.next()
        elif button.emoji.name in ('🔁', '🔂'):  # repeat
            modes = [Repeat.OFF, Repeat.SINGLE, Repeat.ALL]
            index = (modes.index(Repeat(self.player.loop)) + 1) % 3
            self.player.set_loop(modes[index].value)
            await send_message(t('music.repeat_changed', mode=modes[index].name.lower(), user=interaction.user.mention))
        elif button.emoji.name == '🔀':  # shuffle
            self.player.set_shuffle(not self.player.shuffle)
            await send_message(
                t('music.shuffle_changed', mode='on' if self.player.shuffle else 'off', user=interaction.user.mention))
        elif button.emoji.name == '♾️':  # autoplay
            self.player.set_autoplay(not self.player.autoplay)
            await send_message(t('music.autoplay_changed', mode='on' if self.player.autoplay else 'off',
                                 user=interaction.user.mention))
        elif button.emoji.name == '⏏️':  # reset
            await self.player.reset()
            await send_message(t('music.player_controls_pressed', action='reset', user=interaction.user.mention))

    def initialize(self) -> None:
        buttons = [
            Button(emoji='🔀'),
            Button(emoji='⏮️', style=discord.ButtonStyle.primary),
            Button(emoji='⏸️', style=discord.ButtonStyle.primary),
            Button(emoji='⏭️', style=discord.ButtonStyle.primary),
            Button(emoji='🔁'),
            Button(emoji='♾️', label='Autoplay'),
            Button(emoji='⏏️', label='Reset'),
        ]
        self.update_buttons(buttons)

        def callback(*args, **kwargs):
            bot.loop.create_task(self.callback(*args, **kwargs))

        self.view = View.create_button(buttons, callback, timeout=None)

    def get(self) -> View:
        return self.view

    def refresh(self) -> None:
        if not self.view:
            return

        views = self.view.children
        self.view.clear_items()

        for button in self.update_buttons(views):
            self.view.add_item(button)
