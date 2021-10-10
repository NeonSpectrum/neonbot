import asyncio
import inspect

import discord

class Button(discord.ui.Button):
    def __init__(self, **kwargs):
        self._callback = kwargs['callback']
        del kwargs['callback']

        super().__init__(**kwargs)

    def set_callback(self, callback):
        self._callback = callback

    async def callback(self, interaction: discord.Interaction):
        if inspect.iscoroutinefunction(self._callback):
            await self._callback(self, interaction)

class View(discord.ui.View):
    @staticmethod
    def create_button(data, callback, *, timeout=180):
        view = View(timeout=timeout)

        for row in data:
            row['callback'] = callback
            button = Button(**row)
            view.add_item(button)

        return view

    async def on_timeout(self) -> None:
        self.clear_items()
        self.stop()

        if self.msg:
            await self.msg.edit(view=self)

    def set_message(self, msg: discord.Message):
        self.msg = msg