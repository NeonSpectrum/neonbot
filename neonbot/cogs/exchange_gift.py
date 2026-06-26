from typing import Optional, TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from i18n import t

from neonbot.discord_ui.embed import Embed
from neonbot.features.exchange_gift import ExchangeGift
from neonbot.env import OWNER_GUILD_IDS
from neonbot.features.exchange_gift_views import ExchangeGiftView

if TYPE_CHECKING:
    from neonbot import NeonBot


class ExchangeGiftCog(commands.Cog):
    exchangegift = app_commands.Group(
        name='exchangegift',
        description='Exchange gift commands',
        guild_ids=OWNER_GUILD_IDS,
        default_permissions=discord.Permissions(administrator=True),
    )

    def __init__(self, bot: 'NeonBot'):
        self.bot = bot

    @exchangegift.command(name='start')
    async def exchangegift_start(self, interaction: discord.Interaction['NeonBot'], discussion_id: str):
        exchange_gift = ExchangeGift(interaction)

        embed = exchange_gift.create_start_template()

        exchange_gift_message = await interaction.channel.fetch_message(exchange_gift.message_id)

        if not exchange_gift_message:
            message = await interaction.channel.send(
                '@everyone', embed=embed, view=ExchangeGiftView(self.bot.get_channel(int(discussion_id)).jump_url)
            )
            await exchange_gift.set_message_id(message.id)
        else:
            await exchange_gift_message.edit(
                content='@everyone', embed=embed, view=ExchangeGiftView(self.bot.get_channel(int(discussion_id)).jump_url)
            )

        await interaction.response.send_message(embed=Embed(t('exchange_gift.done')), ephemeral=True)

    @exchangegift.command(name='finish')
    async def exchangegift_finish(self, interaction: discord.Interaction['NeonBot']):
        exchange_gift = ExchangeGift(interaction)

        embed = exchange_gift.create_start_template()

        exchange_gift_message = await interaction.channel.fetch_message(exchange_gift.message_id)

        if exchange_gift_message:
            await exchange_gift_message.edit(content='@everyone DONE!', embed=embed, view=None)

        await exchange_gift.set_finish()

        await interaction.response.send_message(embed=Embed(t('exchange_gift.done')), ephemeral=True)

    @exchangegift.command(name='shuffle')
    async def exchangegift_shuffle(self, interaction: discord.Interaction['NeonBot']):
        await ExchangeGift(interaction).shuffle()
        await interaction.response.send_message(
            embed=Embed(t('exchange_gift.shuffled'))
        )

    @exchangegift.command(name='send')
    @app_commands.default_permissions(administrator=True)
    async def exchangegift_send(self, interaction: discord.Interaction['NeonBot'], specific_user: Optional[discord.Member] = None):
        exchange_gift = ExchangeGift(interaction)
        success = []
        failed = []

        no_wishlist_users = exchange_gift.get_no_wishlist_users()

        if len(no_wishlist_users) > 0:
            members = [interaction.guild.get_member(user).mention for user in no_wishlist_users]
            embed = exchange_gift.create_embed_template()
            embed.set_description(t('exchange_gift.missing_wishlist_description'))
            embed.add_field(t('exchange_gift.users'), '\n'.join(members))

            await interaction.response.send_message(embed=embed)
            return

        await interaction.response.defer()

        members = [exchange_gift.get(specific_user.id)] if specific_user else exchange_gift.get_all()

        for member in members:
            user = interaction.guild.get_member(member.user_id)
            chosen_user = interaction.guild.get_member(member.chosen)
            chosen_member = exchange_gift.get(member.chosen)

            embed = exchange_gift.create_embed_template()
            embed.set_description(t('exchange_gift.picked_description'))
            embed.add_field(t('exchange_gift.username'), str(chosen_user))
            embed.add_field(t('exchange_gift.nickname'), chosen_user.nick)
            embed.add_field(t('exchange_gift.budget'), exchange_gift.budget, inline=False)
            embed.add_field(t('exchange_gift.wishlist'), chosen_member.wishlist or 'N/A', inline=False)

            try:
                await user.send(embed=embed)
                success.append(user)
            except discord.Forbidden:
                failed.append(user)

        embed = exchange_gift.create_embed_template()
        embed.add_field(t('exchange_gift.sent_successfully'), '\n'.join(map(lambda u: u.mention, success)))

        if len(failed) > 0:
            embed.add_field(t('exchange_gift.sent_failed'), '\n'.join(map(lambda u: u.mention, failed)))

        await interaction.followup.send(embed=embed)

    @exchangegift.command(name='setbudget')
    async def exchangegift_setbudget(self, interaction: discord.Interaction['NeonBot'], budget: int):
        await ExchangeGift(interaction).set_budget(budget)
        await interaction.response.send_message(
            embed=Embed(t('exchange_gift.budget_set', budget=budget))
        )


async def setup(bot: 'NeonBot') -> None:
    await bot.add_cog(ExchangeGiftCog(bot))
