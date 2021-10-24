import discord
from addict import Dict as DictToObject
from discord.utils import MISSING

from neonbot.classes.view import View


class PlayerControls:
    def __init__(self, player):
        self.player = player

    def update_buttons(self, views):
        for view in views:
            view.style = discord.ButtonStyle.primary

        # ["🔀","⏮️","⏸️","⏭️","🔁"]
        if self.player.connection.is_playing():
            views[2].emoji = "⏸️"
        else:
            views[2].emoji = "▶️"

        if self.player.config['repeat'] == 'off':
            views[4].emoji = "🔁"
            views[4].style = discord.ButtonStyle.secondary
        elif self.player.config['repeat'] == 'single':
            views[4].emoji = "🔂"
            views[4].style = discord.ButtonStyle.primary
        elif self.player.config['repeat'] == 'all':
            views[4].emoji = "🔁"
            views[4].style = discord.ButtonStyle.primary

        views[0].style = discord.ButtonStyle.primary if self.player.config['shuffle'] else discord.ButtonStyle.secondary

        return views

    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        if button.emoji.name == "▶️":  # play
            button.emoji = "⏸️"
            await self.player.refresh_player_message()
            if self.player.connection.is_paused():
                await self.player.resume()
            else:
                self.current_queue = 0
                await self.player.play()
        elif button.emoji.name == "⏸️":  # pause
            button.emoji = "▶️"
            await self.player.refresh_player_message()
            await self.player.pause()
        elif button.emoji.name == "⏮️":  # prev
            self.current_queue -= 2
            await self.player.next()
        elif button.emoji.name == "⏭️":  # next
            await self.player.next()
        elif button.emoji.name in ("🔁", "🔂"):  # repeat
            modes = ["off", "single", "all"]
            index = (modes.index(self.player.config['repeat']) + 1) % 3
            await self.player.repeat(modes[index])
            await self.player.refresh_player_message()
        elif button.emoji.name == "🔀":  # shuffle
            await self.player.shuffle()
            await self.player.refresh_player_message()

    def initialize(self) -> None:
        buttons = [DictToObject(row) for row in [
            {"emoji": "🔀"},
            {"emoji": "⏮️", "disabled": self.current_queue == 0},
            {"emoji": "⏸️" if self.player.connection.is_playing() else "▶️"},
            {"emoji": "⏭️"},
            {"emoji": "🔁"},
        ]]
        self.update_buttons(buttons)

        self.view = View.create_button(buttons, self.callback, timeout=None)

    def get(self) -> View:
        return self.view

    def refresh(self) -> None:
        self.view.children = self.update_buttons(self.view.children)