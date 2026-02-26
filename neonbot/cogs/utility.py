import json
import os
import random
from datetime import datetime
from time import time
from typing import TYPE_CHECKING
from typing import Union

import discord
import psutil
from dateutil.parser import parse
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt

from neonbot import __author__, __title__, __version__
from neonbot.classes.discord.embed import Embed
from neonbot.env import OWNER_GUILD_IDS, SEMAPHONE_API_KEY, SEMAPHONE_SENDER_NAME
from neonbot.utils.constants import ICONS
from neonbot.utils.functions import format_seconds, generate_profile_member_embed, generate_profile_user_embed

if TYPE_CHECKING:
    from neonbot import NeonBot


async def is_owner_guilds(ctx: commands.Context['NeonBot']) -> bool:
    if ctx.guild.id not in ctx.bot.owner_guilds:
        await ctx.reply(
            embed=Embed("You do not have permission to use this command."), ephemeral=True
        )
        return False

    return True


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='random')
    @app_commands.describe(word_list='Word List')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def random(self, interaction: discord.Interaction['NeonBot'], word_list: str) -> None:
        """Picks a text in the given list."""

        await interaction.response.send_message(
            embed=Embed(random.choice(word_list.split(',')).strip())
        )

    @app_commands.command(name='stats')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def status(self, interaction: discord.Interaction['NeonBot']) -> None:
        """Shows the information of the bot."""

        process = psutil.Process(os.getpid())

        embed = Embed()
        embed.set_author(f'{__title__} v{__version__}', icon_url=self.bot.user.display_avatar)
        embed.add_field('Username', self.bot.user.name)
        embed.add_field('Created On', f'{self.bot.user.created_at:%Y-%m-%d %I:%M:%S %p}')
        embed.add_field('Created By', __author__)
        embed.add_field('Guilds', len(self.bot.guilds))
        embed.add_field('Channels', sum(1 for _ in self.bot.get_all_channels()))
        embed.add_field('Users', len(self.bot.users))
        embed.add_field(
            'Ram Usage',
            f'Approximately {(process.memory_info().rss / 1024000):.2f} MB',
            inline=True,
        )
        embed.add_field('Uptime', format_seconds(time() - process.create_time()).split('.')[0])
        embed.add_field(
            'Packages',
            f"""
            discord `{discord.__version__}`
            """,
        )

        await interaction.response.send_message(embed=embed)

    @commands.hybrid_command(name='sms')
    @commands.check(is_owner_guilds)
    @app_commands.guilds(*OWNER_GUILD_IDS)
    async def sms(self, ctx: commands.Context['NeonBot'], number: str, *, body: str) -> None:
        """Send SMS using NeonBot. *BOT_OWNER"""

        def generate_embed():
            embed = Embed()
            embed.set_author(name='✉ SMS')
            embed.set_footer(text='Powered by Semaphore', icon_url=ICONS['semaphone'])
            embed.add_field('To:', number, inline=False)
            embed.add_field('Body:', f'```\n{body}```', inline=False)

            return embed

        message = await ctx.reply(
            embed=generate_embed().add_field('Status:', 'Sending...', inline=False)
        )

        api_key = SEMAPHONE_API_KEY
        sender_name = SEMAPHONE_SENDER_NAME

        body = f'{body}\n\nSent by {ctx.author.display_name}'

        response = await self.bot.session.post(
            'https://api.semaphore.co/api/v4/messages',
            data={'apikey': api_key, 'sendername': sender_name, 'message': body, 'number': number},
        )

        if response.status >= 400:
            data = await response.json()

            await message.edit(
                embed=generate_embed()
                .add_field('Status:', 'Sending failed.', inline=False)
                .add_field('Reason:', json.dumps(data), inline=False)
                .add_field('Date sent:', format_dt(datetime.now()), inline=False)
            )
        else:
            await message.edit(
                embed=generate_embed()
                .add_field('Status:', 'Sent', inline=False)
                .add_field('Date sent:', format_dt(datetime.now()), inline=False)
            )

    @app_commands.command(name='profile')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def profile(self, interaction: discord.Interaction['NeonBot'], user: Union[discord.User, discord.Member], ephemeral: bool = False) -> None:
        if isinstance(user, discord.Member):
            embed = await generate_profile_member_embed(interaction, user)
        else:
            embed = await generate_profile_user_embed(interaction, user)
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.command(name='avatar')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def avatar(self, interaction: discord.Interaction['NeonBot'], user: Union[discord.User, discord.Member], ephemeral: bool = False) -> None:
        if not user.display_avatar:
            await interaction.response.send_message(
                embed=Embed('Avatar not found.'), ephemeral=True
            )
            return

        await interaction.response.send_message(
            user.display_avatar.url, ephemeral=ephemeral
        )

    @app_commands.command(name='banner')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def banner(self, interaction: discord.Interaction['NeonBot'], user: Union[discord.User, discord.Member], ephemeral: bool = False) -> None:
        user = await self.bot.fetch_user(user.id)

        if not user.banner:
            await interaction.response.send_message(
                embed=Embed('Banner not found.'), ephemeral=True
            )
            return

        await interaction.response.send_message(user.banner.url, ephemeral=ephemeral)

    @app_commands.command(name='timestamp')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def timestamp(self, interaction: discord.Interaction['NeonBot'], date_string: str) -> None:
        try:
            timestamp = int(parse(date_string).timestamp())
            await interaction.response.send_message(f'<t:{timestamp}>')
        except ValueError:
            await interaction.response.send_message('Format not supported.',
                                                    ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
