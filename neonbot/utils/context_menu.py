from datetime import datetime
from typing import cast

import discord
from discord import app_commands
from discord.ext.commands import Flag
from discord.utils import format_dt

from neonbot.classes.embed import Embed


def load_context_menu(bot):
    @bot.tree.context_menu(name='Add to Member')
    @app_commands.guilds(discord.Object(id=1008661677446807713))
    @app_commands.default_permissions(administrator=True)
    async def add_to_member(interaction: discord.Interaction, member: discord.Member):
        guest_role = interaction.guild.get_role(1016294997353570305)
        member_role = interaction.guild.get_role(1008661677446807714)

        await member.remove_roles(guest_role)
        await member.add_roles(member_role)

        await cast(discord.InteractionResponse, interaction.response).send_message(
            embed=Embed(f'{member.mention} added to {member_role.mention} role.'),
                                                ephemeral=True)

    @bot.tree.context_menu(name='Profile')
    async def profile(interaction: discord.Interaction, member: discord.Member):
        user = await bot.fetch_user(member.id)
        roles = member.roles[1:]
        flags = [flag.name.title().replace('_', ' ') for flag in member.public_flags.all() if isinstance(flag, Flag)]

        embed = Embed(member.mention, timestamp=datetime.now())
        embed.set_author(str(member), icon_url=member.display_avatar.url)
        embed.set_footer(str(member.id))
        embed.set_thumbnail(member.display_avatar.url)
        embed.add_field("Created", format_dt(member.created_at, 'F'), inline=False)
        embed.add_field("Joined", format_dt(member.joined_at, 'F'), inline=True)
        if member.premium_since:
            embed.add_field("Server Booster since", format_dt(member.premium_since, 'F'), inline=False)
        embed.add_field("Roles", ' '.join([role.mention for role in roles]) if len(roles) > 0 else 'None', inline=False)
        embed.add_field("Badges", '\n'.join(flags) if len(flags) > 0 else 'None', inline=False)

        if user.banner:
            embed.set_image(user.banner.url)

        await cast(discord.InteractionResponse, interaction.response).send_message(embed=embed, ephemeral=True)
