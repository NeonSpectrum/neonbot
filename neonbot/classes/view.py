import inspect

import nextcord


class Button(nextcord.ui.Button):
    def __init__(self, **kwargs):
        self._callback = kwargs['callback']
        del kwargs['callback']

        super().__init__(**kwargs)

    def set_callback(self, callback):
        self._callback = callback

    async def callback(self, interaction: nextcord.Interaction):
        if inspect.iscoroutinefunction(self._callback):
            await self._callback(self, interaction)


class View(nextcord.ui.View):
    def __init__(self, **kwargs):
        self.msg = None
        super().__init__(**kwargs)

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
            try:
                await self.msg.edit(view=self)
            except nextcord.NotFound:
                pass

    async def on_error(self, error: Exception, item: nextcord.ui.Item, interaction: nextcord.Interaction) -> None:
        if isinstance(error, nextcord.NotFound):
            return

        return await super().on_error(error, item, interaction)

    def set_message(self, msg: nextcord.Message):
        self.msg = msg
