import random
from datetime import datetime
from typing import Optional

import discord
from discord.utils import find

from neonbot.classes.embed import Embed
from neonbot.models.guild import Guild
from neonbot.utils.exceptions import ExchangeGiftNotRegistered


class ExchangeGift:
    def __init__(self, interaction: discord.Interaction):
        self.db = Guild.get_instance(interaction.guild)
        self.user = interaction.user

    def get(self, user_id: Optional[int] = None):
        user_id = user_id or self.user.id
        return find(lambda member: member['user_id'] == user_id, self.get_all())

    @property
    def budget(self):
        return self.db.get('exchange_gift.budget')

    def get_all(self):
        return self.db.get('exchange_gift.members', [])

    def get_no_wishlist_users(self):
        no_wishlist_users = []

        for member in self.get_all():
            if member['wishlist'] is None:
                no_wishlist_users.append(member['user_id'])

        return no_wishlist_users

    async def set_budget(self, budget):
        await self.db.update({'exchange_gift.budget': budget})

    async def set_wishlist(self, wishlist: str):
        if not self.get():
            raise ExchangeGiftNotRegistered()

        await self.db.update({
            'exchange_gift.members.$.wishlist': wishlist
        }, where={
            'exchange_gift.members.user_id': self.user.id
        })

    def get_wishlist(self):
        if not self.get():
            raise ExchangeGiftNotRegistered()

        return self.get()['wishlist']

    async def register(self):
        await self.db.collection.update_one(self.db.where, {
            '$push': {
                'exchange_gift.members': {
                    'user_id': self.user.id,
                    'wishlist': None,
                    'chosen': None
                }
            }
        })
        await self.db.refresh()

    async def unregister(self):
        if not self.get():
            raise ExchangeGiftNotRegistered()

        await self.db.collection.update_one(self.db.where, {
            '$pull': {
                'exchange_gift.members': {
                    'user_id': self.user.id,
                }
            }
        })
        await self.db.refresh()

    async def shuffle(self):
        members = list(map(lambda m: m['user_id'], self.get_all()))

        if len(members) <= 1:
            return

        for member in self.get_all():
            chosen_member = random.choice([m for m in members if m != member['user_id']])
            members.remove(chosen_member)

            await self.db.update({
                'exchange_gift.members.$.chosen': chosen_member
            }, where={
                'exchange_gift.members.user_id': member['user_id']
            })

    def create_embed_template(self):
        year = datetime.now().strftime('%Y')
        return Embed().set_author('🎁 Exchange Gift for ' + year)
