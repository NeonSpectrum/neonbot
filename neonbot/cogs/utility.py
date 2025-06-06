import os
import random
from datetime import datetime
from io import BytesIO
from time import time
from typing import cast

import discord
import psutil
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt
from envparse import env
from yt_dlp import version as ytdl_version

from neonbot import __author__, __title__, __version__, bot
from neonbot.classes.embed import Embed
from neonbot.classes.gemini import GeminiChat
from neonbot.utils.constants import ICONS
from neonbot.utils.functions import format_seconds, md_to_text


class Utility(commands.Cog):
    @app_commands.command(name='random')
    @app_commands.describe(word_list='Word List')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def random(self, interaction: discord.Interaction, word_list: str) -> None:
        """Picks a text in the given list."""

        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed(random.choice(word_list.split(',')).strip()))

    @app_commands.command(name='stats')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def status(self, interaction: discord.Interaction) -> None:
        """Shows the information of the bot."""

        process = psutil.Process(os.getpid())

        embed = Embed()
        embed.set_author(f"{__title__} v{__version__}", icon_url=bot.user.display_avatar)
        embed.add_field("Username", bot.user.name)
        embed.add_field("Created On", f"{bot.user.created_at:%Y-%m-%d %I:%M:%S %p}")
        embed.add_field("Created By", __author__)
        embed.add_field("Guilds", len(bot.guilds))
        embed.add_field("Channels", sum(1 for _ in bot.get_all_channels()))
        embed.add_field("Users", len(bot.users))
        embed.add_field(
            "Ram Usage",
            f"Approximately {(process.memory_info().rss / 1024000):.2f} MB",
            inline=True,
        )
        embed.add_field(
            "Uptime", format_seconds(time() - process.create_time()).split(".")[0]
        )
        embed.add_field(
            "Packages",
            f"""
            discord `{discord.__version__}`
            youtube-dl `{ytdl_version.__version__}`
            """
        )

        await cast(discord.InteractionResponse, interaction.response).send_message(embed=embed)

    @app_commands.command(name='sms')
    @app_commands.guilds(*bot.owner_guilds)
    async def sms(self, interaction: discord.Interaction, number: str, message: str) -> None:
        """Send SMS using NeonBot. *BOT_OWNER"""

        def generate_embed():
            embed = Embed()
            embed.set_author(name="✉ SMS")
            embed.set_footer(
                text="Powered by Semaphore",
                icon_url=ICONS['semaphone']
            )
            embed.add_field("To:", number, inline=True)
            embed.add_field("Body:", message, inline=True)

            return embed

        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=generate_embed().add_field("Status:", "Sending...", inline=False))

        api_key = env.str("SEMAPHONE_API_KEY")
        sender_name = env.str("SEMAPHONE_SENDER_NAME")

        body = f"{message}\n\nSent by {interaction.user}"

        response = await bot.session.post(
            f"https://api.semaphore.co/api/v4/messages",
            data={
                "apikey": api_key,
                "sendername": sender_name,
                "message": body,
                "number": number
            }
        )

        if response.status >= 400:
            data = await response.json()

            await interaction.edit_original_response(
                embed=generate_embed().add_field("Status:", "Sending failed.", inline=False)
                .add_field("Reason:", data['status'], inline=False)
                .add_field("Date sent:", format_dt(datetime.now()), inline=False)
            )
        else:
            await interaction.edit_original_response(
                embed=generate_embed().add_field("Status:", "Sent", inline=False)
                .add_field("Date sent:", format_dt(datetime.now()), inline=False)
            )

    @app_commands.command(name='ask')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ask(self, interaction: discord.Interaction, prompt: str) -> None:
        """Ask AI."""

        await cast(discord.InteractionResponse, interaction.response).defer()

        gemini_chat = GeminiChat(prompt)
        gemini_chat.set_prompt_concise()

        await gemini_chat.generate_content()

        await interaction.followup.send(gemini_chat.get_response())


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility())
