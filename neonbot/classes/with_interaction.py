import discord

from neonbot import bot


class WithInteraction:
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction

    async def send_message(self, *args, **kwargs):
        await bot.send_response(self.interaction, *args, **kwargs)
