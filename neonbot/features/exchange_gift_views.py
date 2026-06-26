from typing import Optional, TYPE_CHECKING

import discord
from i18n import t

from neonbot.discord_ui.embed import Embed
from neonbot.features.exchange_gift import ExchangeGift
from neonbot.utils.exceptions import ExchangeGiftNotRegistered

if TYPE_CHECKING:
    from neonbot import NeonBot


class WishlistModal(discord.ui.Modal, title=t('exchange_gift.modal_set_wishlist_title')):
    def __init__(self, parent: Optional[discord.Interaction['NeonBot']] = None):
        super().__init__()
        self.parent = parent

    wishlist = discord.ui.TextInput(
        label=t('exchange_gift.modal_wishlist_label'),
        placeholder=t('exchange_gift.modal_wishlist_placeholder'),
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction['NeonBot']):
        try:
            wishlist = self.wishlist.value

            exchange_gift = ExchangeGift(interaction)
            await exchange_gift.set_wishlist(wishlist)

            if self.parent:
                await interaction.response.defer()
                await self.parent.edit_original_response(embed=Embed(t('exchange_gift.your_wishlist', wishlist=wishlist)))
            else:
                await interaction.response.send_message(
                    embed=Embed(t('exchange_gift.wishlist_updated')), ephemeral=True
                )
        except ExchangeGiftNotRegistered:
            await interaction.response.send_message(
                embed=Embed(t('exchange_gift.not_registered')), ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                embed=Embed(t('exchange_gift.wishlist_save_error')), ephemeral=True
            )


class WishlistView(discord.ui.View):
    def __init__(self, parent: discord.Interaction['NeonBot']):
        super().__init__(timeout=None)
        self.parent = parent

    @discord.ui.button(label=t('exchange_gift.button_edit_wishlist'), custom_id='exchange_gift:edit_wishlist')
    async def edit_wishlist(self, interaction: discord.Interaction['NeonBot'], button: discord.ui.Button):
        await interaction.response.send_modal(WishlistModal(self.parent))


class ExchangeGiftView(discord.ui.View):
    def __init__(self, discussion_url: str = None):
        super().__init__(timeout=None)

        if discussion_url:
            self.add_item(discord.ui.Button(label=t('exchange_gift.button_go_to_discussions'), url=discussion_url, emoji='💬'))

    @discord.ui.button(
        label=t('exchange_gift.button_participate'), style=discord.ButtonStyle.primary, custom_id='exchange_gift:participate', emoji='✅'
    )
    async def participate(self, interaction: discord.Interaction['NeonBot'], button: discord.ui.Button):
        exchange_gift = ExchangeGift(interaction)

        if exchange_gift.member:
            await interaction.response.send_message(
                embed=Embed(t('exchange_gift.already_registered')), ephemeral=True
            )
            return

        await exchange_gift.register()
        await interaction.response.send_message(
            embed=Embed(t('exchange_gift.registered')), ephemeral=True
        )

    @discord.ui.button(label=t('exchange_gift.button_my_wishlist'), custom_id='exchange_gift:my_wishlist', emoji='🎁')
    async def my_wishlist(self, interaction: discord.Interaction['NeonBot'], button: discord.ui.Button):
        try:
            exchange_gift = ExchangeGift(interaction)
            wishlist = exchange_gift.get_wishlist()

            if not wishlist:
                await interaction.response.send_modal(WishlistModal())
            else:
                view = WishlistView(interaction)
                message = await interaction.response.send_message(
                    embed=Embed(t('exchange_gift.your_wishlist', wishlist=wishlist)), view=view, ephemeral=True
                )

        except ExchangeGiftNotRegistered as error:
            await interaction.response.send_message(
                embed=Embed(error), ephemeral=True
            )

    @discord.ui.button(label=t('exchange_gift.button_all_wishlist'), custom_id='exchange_gift:all_wishlist', emoji='🎁')
    async def all_wishlist(self, interaction: discord.Interaction['NeonBot'], button: discord.ui.Button):
        try:
            exchange_gift = ExchangeGift(interaction)
            wishlist = exchange_gift.get_wishlist()

            template = []

            for member in exchange_gift.get_all():
                user = interaction.guild.get_member(member.user_id)
                if not user:
                    continue
                template.append(f'{user.mention}\n```{member.wishlist}```')

            embed = exchange_gift.create_wishlist_template()
            embed.set_description(''.join(template))

            message = await interaction.response.send_message(
                embed=embed, ephemeral=True
            )

        except ExchangeGiftNotRegistered as error:
            await interaction.response.send_message(
                embed=Embed(error), ephemeral=True
            )

    @discord.ui.button(label=t('exchange_gift.button_get_event_info'), custom_id='exchange_gift:get_event_info', emoji='📄')
    async def get_event_info(self, interaction: discord.Interaction['NeonBot'], button: discord.ui.Button):
        exchange_gift = ExchangeGift(interaction)
        await interaction.response.send_message(
            embed=exchange_gift.get_current_info(), ephemeral=True
        )
