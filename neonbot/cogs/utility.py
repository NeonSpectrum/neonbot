import os
import random
from datetime import datetime
from time import time
from typing import Optional

import discord
import psutil
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt
from envparse import env
from yt_dlp import version as ytdl_version

from .. import __author__, __title__, __version__, bot
from ..classes.embed import Embed
from ..classes.exchange_gift import ExchangeGift
from ..utils.constants import ICONS
from ..utils.exceptions import ExchangeGiftNotRegistered
from ..utils.functions import format_seconds, is_owner


class Utility(commands.Cog):
    exchangegift = app_commands.Group(name='exchangegift', description="Exchange gift commands",
                                      guild_ids=bot.owner_guilds)

    @app_commands.command(name='random')
    @app_commands.describe(word_list='Word List')
    async def random(self, interaction: discord.Interaction, word_list: str) -> None:
        """Picks a text in the given list."""

        await interaction.response.send_message(embed=Embed(random.choice(word_list.split(',')).strip()))

    @app_commands.command(name='stats')
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

        await interaction.response.send_message(embed=embed)

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

        await interaction.response.send_message(embed=generate_embed().add_field("Status:", "Sending...", inline=False))

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

    @exchangegift.command(name='register')
    async def exchangegift_register(self, interaction: discord.Interaction):
        exchange_gift = ExchangeGift(interaction)

        if exchange_gift.member:
            await interaction.response.send_message(
                embed=Embed('You are already registered in the exchange gift event.'),
                ephemeral=True
            )
            return

        await exchange_gift.register()
        await interaction.response.send_message(embed=Embed('You have been registered in the exchange gift event.'))

    @exchangegift.command(name='unregister')
    async def exchangegift_unregister(self, interaction: discord.Interaction):
        exchange_gift = ExchangeGift(interaction)

        try:
            await exchange_gift.unregister()
            await interaction.response.send_message(
                embed=Embed('You have been unregistered in the exchange gift event.')
            )
        except ExchangeGiftNotRegistered as error:
            await interaction.response.send_message(embed=Embed(error))

    @exchangegift.command(name='shuffle')
    async def exchangegift_shuffle(self, interaction: discord.Interaction):
        if not is_owner(interaction):
            return

        await ExchangeGift(interaction).shuffle()
        await interaction.response.send_message(embed=Embed(f'Exchange gift has been shuffled.'))

    @exchangegift.command(name='send')
    @app_commands.default_permissions(administrator=True)
    async def exchangegift_send(self, interaction: discord.Interaction, specific_user: Optional[discord.Member] = None):
        if not is_owner(interaction):
            return

        exchange_gift = ExchangeGift(interaction)
        success = []
        failed = []

        no_wishlist_users = exchange_gift.get_no_wishlist_users()

        if len(no_wishlist_users) > 0:
            members = [interaction.guild.get_member(user).mention for user in no_wishlist_users]
            embed = exchange_gift.create_embed_template()
            embed.set_description(
                'There are some users without wishlist.\
                Pleae add wishlist first before proceeding, so everyone can have a basis on what gift to buy.'
            )
            embed.add_field('Users:', "\n".join(members))

            await interaction.response.send_message(embed=embed)
            return

        await interaction.response.defer()

        members = [exchange_gift.get(specific_user.id)] if specific_user else exchange_gift.get_all()

        for member in members:
            user = interaction.guild.get_member(member['user_id'])
            embed = exchange_gift.create_embed_template()
            embed.set_description('You will have to gift this person for Christmas.')
            embed.add_field('Username', str(user))
            embed.add_field('Nickname', user.nick)
            embed.add_field('Budget', exchange_gift.budget, inline=False)
            embed.add_field('Wishlist', member.get('wishlist', 'N/A'), inline=False)

            try:
                await user.send(embed=embed)
                success.append(user)
            except discord.Forbidden:
                failed.append(user)

        embed = exchange_gift.create_embed_template()
        embed.add_field('Sent successfully:', "\n".join(map(lambda u: u.mention, success)))

        if len(failed) > 0:
            embed.add_field('Sent failed:', "\n".join(map(lambda u: u.mention, failed)))

        await interaction.followup.send(embed=embed)

    @exchangegift.command(name='budget')
    async def exchangegift_budget(self, interaction: discord.Interaction):
        budget = ExchangeGift(interaction).budget
        await interaction.response.send_message(embed=Embed(f'The current budget is `{budget}`.'))

    @exchangegift.command(name='setbudget')
    async def exchangegift_setbudget(self, interaction: discord.Interaction, budget: int):
        if not is_owner(interaction):
            return

        await ExchangeGift(interaction).set_budget(budget)
        await interaction.response.send_message(embed=Embed(f'Budget has been set to `{budget}`.'))

    @exchangegift.command(name='wishlist')
    async def exchangegift_getwishlist(self, interaction: discord.Interaction):
        try:
            wishlist = ExchangeGift(interaction).get_wishlist()

            await interaction.response.send_message(embed=Embed(f'Your current wishlist is `{wishlist}`.'),
                                                    ephemeral=True)
        except ExchangeGiftNotRegistered as error:
            await interaction.response.send_message(embed=Embed(error))

    @exchangegift.command(name='setwishlist')
    async def exchangegift_setwishlist(self, interaction: discord.Interaction, wishlist: str):
        try:
            await ExchangeGift(interaction).set_wishlist(wishlist)
            await interaction.response.send_message(embed=Embed('Your wishlist has been updated.'), ephemeral=True)
        except ExchangeGiftNotRegistered as error:
            await interaction.response.send_message(embed=Embed(error))


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility())
