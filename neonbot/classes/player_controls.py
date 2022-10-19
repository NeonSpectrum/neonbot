from typing import TYPE_CHECKING

import discord
from i18n import t

from .embed import Embed
from .view import View, Button
from ..enums import Repeat

if TYPE_CHECKING:
    from .player import Player


class PlayerControls:
    def __init__(self, player):
        self.player: Player = player
        self.view = None

    def update_buttons(self, views):
        for view in views:
            view.style = discord.ButtonStyle.primary

        # ["🔀","⏮️","⏸️","⏭️","🔁"]
        if self.player.connection.is_playing():
            views[2].emoji = "⏸️"
        else:
            views[2].emoji = "▶️"

        if self.player.repeat == Repeat.OFF:
            views[4].emoji = "🔁"
            views[4].style = discord.ButtonStyle.secondary
        elif self.player.repeat == Repeat.SINGLE:
            views[4].emoji = "🔂"
            views[4].style = discord.ButtonStyle.primary
        elif self.player.repeat == Repeat.ALL:
            views[4].emoji = "🔁"
            views[4].style = discord.ButtonStyle.primary

        if self.player.is_shuffle:
            views[0].style = discord.ButtonStyle.primary
        else:
            views[0].style = discord.ButtonStyle.secondary

        return views

    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        # await interaction.response.send_message(embed=Embed(f"{interaction.user} clicked {button.emoji.name}"),
        #                                         ephemeral=True)

        if button.emoji.name == "▶️":  # play
            if self.player.connection.is_paused():
                await self.player.resume(requester=interaction.user)
            else:
                self.player.current_queue = 0
                await self.player.play()
        elif button.emoji.name == "⏸️":  # pause
            await self.player.pause(requester=interaction.user)
        elif button.emoji.name == "⏮️":  # prev
            if self.player.current_queue == 0:
                self.player.current_queue = len(self.player.queue) - 2
            else:
                self.player.current_queue -= 2

            self.player.next()
            await interaction.channel.send(
                embed=Embed(t('music.player_controls_pressed', action='back', user=interaction.user.mention))
            )
        elif button.emoji.name == "⏭️":  # next
            self.player.next()
            await interaction.channel.send(
                embed=Embed(t('music.player_controls_pressed', action='next', user=interaction.user.mention))
            )
        elif button.emoji.name in ("🔁", "🔂"):  # repeat
            modes = [Repeat.OFF, Repeat.SINGLE, Repeat.ALL]
            index = (modes.index(Repeat(self.player.repeat)) + 1) % 3
            await self.player.set_repeat(modes[index], requester=interaction.user)
        elif button.emoji.name == "🔀":  # shuffle
            await self.player.set_shuffle(requester=interaction.user)

    def initialize(self) -> None:
        buttons = [
            Button(emoji="🔀"),
            Button(emoji="⏮️"),
            Button(emoji="⏸️"),
            Button(emoji="⏭️"),
            Button(emoji="🔁"),
        ]
        self.update_buttons(buttons)

        self.view = View.create_button(buttons, self.callback, timeout=None)

    def get(self) -> View:
        return self.view

    def refresh(self) -> None:
        if not self.view:
            return

        views = self.view.children
        self.view.clear_items()

        for button in self.update_buttons(views):
            self.view.add_item(button)
