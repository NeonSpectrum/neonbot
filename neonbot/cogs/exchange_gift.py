import os
import random
from datetime import datetime
from time import time
from typing import Optional

import discord
import openai
import psutil
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt
from envparse import env
from yt_dlp import version as ytdl_version

from .. import __author__, __title__, __version__, bot
from ..classes.embed import Embed
from ..classes.exchange_gift import ExchangeGift
from ..views.ExchangeGiftView import ExchangeGiftView


class ExchangeGiftCog(commands.Cog):
    exchangegift = app_commands.Group(name='exchangegift', description="Exchange gift commands",
                                      guild_ids=bot.owner_guilds,
                                      default_permissions=discord.Permissions(administrator=True))

    @exchangegift.command(name='start')
    async def exchangegift_start(self, interaction: discord.Interaction, discussion_id: str):
        exchange_gift = ExchangeGift(interaction)

        embed = exchange_gift.create_start_template()

        exchange_gift_message = await interaction.channel.fetch_message(exchange_gift.message_id)

        if not exchange_gift_message:
            message = await interaction.channel.send('@everyone', embed=embed,
                                                     view=ExchangeGiftView(
                                                         bot.get_channel(int(discussion_id)).jump_url))
            await exchange_gift.set_message_id(message.id)
        else:
            await exchange_gift_message.edit(content='@everyone', embed=embed,
                                             view=ExchangeGiftView(
                                                 bot.get_channel(int(discussion_id)).jump_url))

        await interaction.response.send_message(embed=Embed('Done!'), ephemeral=True)

    @exchangegift.command(name='finish')
    async def exchangegift_finish(self, interaction: discord.Interaction):
        exchange_gift = ExchangeGift(interaction)

        embed = exchange_gift.create_start_template()

        exchange_gift_message = await interaction.channel.fetch_message(exchange_gift.message_id)

        if exchange_gift_message:
            await exchange_gift_message.edit(content='@everyone DONE!', embed=embed, view=None)

        await exchange_gift.set_finish()

        await interaction.response.send_message(embed=Embed('Done!'), ephemeral=True)

    @exchangegift.command(name='shuffle')
    async def exchangegift_shuffle(self, interaction: discord.Interaction):
        await ExchangeGift(interaction).shuffle()
        await interaction.response.send_message(embed=Embed(f'Exchange gift has been shuffled.'))

    @exchangegift.command(name='send')
    @app_commands.default_permissions(administrator=True)
    async def exchangegift_send(self, interaction: discord.Interaction, specific_user: Optional[discord.Member] = None):
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
            user = interaction.guild.get_member(member.user_id)
            chosen_user = interaction.guild.get_member(member.chosen)
            chosen_member = exchange_gift.get(member.chosen)

            embed = exchange_gift.create_embed_template()
            embed.set_description('You have picked this person as your gift recipient for the event! '
                                  'Please refer to the following details for more information, and remember to refrain from sharing this to others!')
            embed.add_field('Username', str(chosen_user))
            embed.add_field('Nickname', chosen_user.nick)
            embed.add_field('Budget', exchange_gift.budget, inline=False)
            embed.add_field('Wishlist', chosen_member.wishlist or 'N/A', inline=False)

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

    @exchangegift.command(name='setbudget')
    async def exchangegift_setbudget(self, interaction: discord.Interaction, budget: int):
        await ExchangeGift(interaction).set_budget(budget)
        await interaction.response.send_message(embed=Embed(f'Budget has been set to `{budget}`.'))


# noinspection PyShadowingNames
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ExchangeGiftCog())
