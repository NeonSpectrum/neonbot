import asyncio
import re
from datetime import datetime, timedelta
from typing import Union

import discord
import markdown
import pytz
from bs4 import BeautifulSoup
from discord.utils import format_dt
from envparse import env

from neonbot.classes.embed import Embed


async def shell_exec(command: str) -> str:
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    return stdout.decode().strip()


def get_command_string(interaction: discord.Interaction):
    params = []

    # Context menu starts with uppercase
    if interaction.command.name[0].isupper():
        try:
            users = list(interaction.data['resolved']['users'].values())
            params = [f'{user["username"]}#{user["discriminator"]}' for user in users]
        except IndexError:
            pass
    else:
        params = [f'{key}="{value}"' for key, value in interaction.namespace.__dict__.items()]

    return f'{interaction.command.name} {" ".join(params)}'


def format_seconds(secs: Union[int, float]) -> str:
    formatted = str(timedelta(seconds=secs)).split('.')[0]
    if formatted.startswith('0:'):
        return formatted[2:]
    return formatted


def format_uptime(milliseconds: int) -> str:
    td = str(timedelta(milliseconds=milliseconds)).split(':')
    msg = []

    if td[0] != '0':
        msg.append(f'{td[0]} Hours')

    msg.append(f'{int(td[1]):.0f} Minutes {round(float(td[2]))} Seconds')

    return ' '.join(msg)


def get_log_prefix() -> str:
    tz = pytz.timezone(env.str('TZ', default='Asia/Manila'))
    now = datetime.now(tz)
    return f'[{now.strftime("%I:%M:%S %p")}] :bust_in_silhouette:'


def split_long_message(text: str):
    if len(text) < 2000:
        return [text]

    lines = text.split('\n')
    messages = []
    message = ''

    for line in lines:
        if len(message) + len(line) + 1 > 2000:
            messages.append(message)
            message = line + '\n'
        else:
            message += line + '\n'

    if message:
        messages.append(message)

    return messages


def md_to_text(md):
    html = markdown.markdown(md)
    soup = BeautifulSoup(html, features='html.parser')
    return soup.get_text()


def remove_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


async def generate_profile_member_embed(member: discord.Member):
    roles = member.roles[1:]
    # noinspection PyUnresolvedReferences
    flags = [flag.name.title().replace('_', ' ') for flag in member.public_flags.all()]

    embed = Embed(member.mention, timestamp=datetime.now())
    embed.set_author(str(member), icon_url=member.display_avatar.url)
    embed.set_footer(str(member.id))
    embed.set_thumbnail(member.display_avatar.url)
    embed.add_field('Created', format_dt(member.created_at, 'F'), inline=False)
    embed.add_field('Joined', format_dt(member.joined_at, 'F'), inline=True)
    if member.premium_since:
        embed.add_field('Server Booster since', format_dt(member.premium_since, 'F'), inline=False)
    embed.add_field('Roles', ' '.join([role.mention for role in roles]) if len(roles) > 0 else 'None', inline=False)
    embed.add_field('Badges', '\n'.join(flags) if len(flags) > 0 else 'None', inline=False)

    if member.banner:
        embed.set_image(member.banner.url)

    return embed


async def generate_profile_user_embed(user: discord.User):
    # noinspection PyUnresolvedReferences
    flags = [flag.name.title().replace('_', ' ') for flag in user.public_flags.all()]

    embed = Embed(user.mention, timestamp=datetime.now())
    embed.set_author(str(user), icon_url=user.display_avatar.url)
    embed.set_footer(str(user.id))
    embed.set_thumbnail(user.display_avatar.url)
    embed.add_field('Created', format_dt(user.created_at, 'F'), inline=False)
    embed.add_field('Joined', format_dt(user.joined_at, 'F'), inline=True)
    embed.add_field('Badges', '\n'.join(flags) if len(flags) > 0 else 'None', inline=False)

    if user.banner:
        embed.set_image(user.banner.url)

    return embed
