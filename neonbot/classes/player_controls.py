import discord

from .view import View, Button
from ..enums import Repeat


class PlayerControls:
    def __init__(self, player):
        self.player = player
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
                await self.player.resume()
            else:
                self.player.current_queue = 0
                await self.player.play()
        elif button.emoji.name == "⏸️":  # pause
            await self.player.pause()
        elif button.emoji.name == "⏮️":  # prev
            self.player.current_queue -= 2
            self.player.next()
        elif button.emoji.name == "⏭️":  # next
            self.player.next()
        elif button.emoji.name in ("🔁", "🔂"):  # repeat
            modes = [Repeat.OFF, Repeat.SINGLE, Repeat.ALL]
            index = (modes.index(Repeat(self.player.repeat)) + 1) % 3
            await self.player.set_repeat(modes[index])
        elif button.emoji.name == "🔀":  # shuffle
            await self.player.set_shuffle()

    def initialize(self) -> None:
        buttons = [
            Button(emoji="🔀"),
            Button(emoji="⏮️", disabled=self.player.current_queue == 0),
            Button(emoji="⏸️"),
            Button(emoji="⏭️"),
            Button(emoji="🔁"),
        ]
        self.update_buttons(buttons)

        self.view = View.create_button(buttons, self.callback, timeout=None)

    def get(self) -> View:
        return self.view

    def refresh(self) -> None:
        views = self.view.children
        self.view.clear_items()

        for button in self.update_buttons(views):
            self.view.add_item(button)
