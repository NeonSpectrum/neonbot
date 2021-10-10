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

class View:
    @staticmethod
    def create_button(data, callback):
        view = discord.ui.View()

        for row in data:
            row['callback'] = callback
            button = Button(**row)
            view.add_item(button)

        return view