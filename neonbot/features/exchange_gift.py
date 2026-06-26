import random
from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord.utils import find
from i18n import t

from neonbot.discord_ui.embed import Embed
from neonbot.models.exchange_gift import ExchangeGiftMember
from neonbot.models.guild import GuildModel
from neonbot.utils.exceptions import ExchangeGiftNotRegistered

if TYPE_CHECKING:
    from neonbot import NeonBot


class ExchangeGift:
    def __init__(self, interaction: discord.Interaction['NeonBot']):
        self.server = GuildModel.get_instance(interaction.guild.id)
        self.bot = interaction.client
        self.guild = interaction.guild
        self.user = interaction.user

    def get(self, user_id):
        return find(lambda member: member.user_id == user_id, self.get_all())

    @property
    def member(self):
        return find(lambda member: member.user_id == self.user.id, self.get_all())

    @property
    def budget(self):
        return self.server.exchange_gift.budget

    @property
    def message_id(self):
        return self.server.exchange_gift.message_id

    def get_all(self):
        return self.server.exchange_gift.members

    async def set_message_id(self, message_id: int):
        self.server.exchange_gift.message_id = message_id
        await self.server.save_changes(False)

    def get_no_wishlist_users(self):
        no_wishlist_users = []

        for member in self.get_all():
            if member.wishlist is None:
                no_wishlist_users.append(member.user_id)

        return no_wishlist_users

    async def set_budget(self, budget):
        self.server.exchange_gift.budget = budget
        await self.server.save_changes(False)

    async def set_wishlist(self, wishlist: str):
        if not self.member:
            raise ExchangeGiftNotRegistered()

        self.member.wishlist = wishlist

        await self.server.save_changes(False)

    def get_wishlist(self):
        if not self.member:
            raise ExchangeGiftNotRegistered()

        return self.member.wishlist

    async def register(self):
        self.server.exchange_gift.members.append(ExchangeGiftMember(user_id=self.user.id))
        await self.server.save_changes(False)

    async def unregister(self):
        if not self.member:
            raise ExchangeGiftNotRegistered()

        self.server.exchange_gift.members.remove(ExchangeGiftMember(user_id=self.user.id))
        await self.server.save_changes(False)

    async def shuffle(self):
        all_members = list(self.get_all())
        member_ids = [m.user_id for m in all_members]

        if len(member_ids) <= 1:
            return

        # Create a derangement: shuffle until no one is assigned to themselves
        shuffled_ids = member_ids.copy()
        while True:
            random.shuffle(shuffled_ids)
            if all(a != b for a, b in zip(member_ids, shuffled_ids)):
                break

        for member, chosen_id in zip(all_members, shuffled_ids):
            member.chosen = chosen_id

        await self.server.save_changes(False)

    async def set_finish(self):
        self.server.exchange_gift.finish = True
        await self.server.save_changes(False)

    def create_embed_template(self):
        year = datetime.now().strftime('%Y')
        return Embed().set_author(t('exchange_gift.event_title', year=year))

    def create_wishlist_template(self):
        year = datetime.now().strftime('%Y')
        return Embed().set_author(t('exchange_gift.wishlist_title', year=year))

    def create_start_template(self):
        embed = self.create_embed_template()
        embed.set_description(t('exchange_gift.event_description', owner=self.bot.app_info.owner.mention))

        return embed

    def get_current_info(self):
        members = [self.guild.get_member(member.user_id).mention for member in self.get_all()]

        embed = self.create_embed_template()
        embed.add_field(t('exchange_gift.budget_label'), self.budget)
        embed.add_field(t('exchange_gift.participants_label'), ' '.join(members), inline=False)

        return embed
