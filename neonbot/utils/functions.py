import asyncio
import re
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from typing import Union

import discord
import markdown
import pytz
from bs4 import BeautifulSoup
from discord.ext import commands
from discord.utils import format_dt
from i18n import t

from neonbot.discord_ui.embed import Embed
from neonbot.env import TZ

if TYPE_CHECKING:
    from neonbot import NeonBot


async def shell_exec(command: str) -> str:
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    output = stdout.decode().strip()
    if not output and stderr:
        output = stderr.decode().strip()
    return output


def get_command_string(ctx: commands.Context['NeonBot']):
    if ctx.interaction:
        interaction = ctx.interaction
        params = []

        # Context menu starts with uppercase
        if ctx.command.name[0].isupper():
            try:
                users = list(interaction.data['resolved']['users'].values())
                params = [f'{user["username"]}#{user["discriminator"]}' for user in users]
            except IndexError:
                pass
        else:
            params = [f'{key}="{value}"' for key, value in interaction.namespace.__dict__.items()]

        return f'{interaction.command.name} {" ".join(params)}'
    else:
        command_name = ctx.invoked_with if ctx.invoked_with != 'bot' else ctx.command.name

        params = ctx.message.content[len(ctx.prefix + command_name):].strip()
        return f'{ctx.prefix}{command_name} {params}'


def format_seconds(secs: Union[int, float]) -> str:
    formatted = str(timedelta(seconds=secs)).split('.')[0]
    if formatted.startswith('0:'):
        return formatted[2:]
    return formatted


def format_milliseconds(ms: Union[int, float]) -> str:
    return format_seconds(ms / 1000)


def format_uptime(milliseconds: int) -> str:
    td = str(timedelta(milliseconds=milliseconds)).split(':')
    msg = []

    if td[0] != '0':
        msg.append(f'{td[0]} {t("common.hours")}')

    msg.append(f'{int(td[1]):.0f} {t("common.minutes")} {round(float(td[2]))} {t("common.seconds")}')

    return ' '.join(msg)


def get_log_prefix() -> str:
    tz = pytz.timezone(TZ)
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


async def generate_profile_member_embed(interaction: discord.Interaction['NeonBot'], member: discord.Member):
    user = await interaction.client.fetch_user(member.id)

    roles = member.roles[1:]
    # noinspection PyUnresolvedReferences
    flags = [flag.name.title().replace('_', ' ') for flag in member.public_flags.all()]

    embed = Embed(member.mention, timestamp=datetime.now())
    embed.set_author(str(member), icon_url=member.display_avatar.url)
    embed.set_footer(str(member.id))
    embed.add_field(t('utility.profile.created'), format_dt(member.created_at, 'F'), inline=False)
    embed.add_field(t('utility.profile.joined'), format_dt(member.joined_at, 'F'), inline=True)
    if member.premium_since:
        embed.add_field(t('utility.profile.server_booster_since'), format_dt(member.premium_since, 'F'), inline=False)
    embed.add_field(t('utility.profile.roles'), ' '.join([role.mention for role in roles]) if len(roles) > 0 else t('utility.profile.none'), inline=False)
    embed.add_field(t('utility.profile.badges'), '\n'.join(flags) if len(flags) > 0 else t('utility.profile.none'), inline=False)

    if user.display_avatar:
        embed.set_thumbnail(member.display_avatar.url)

    if user.banner:
        embed.set_image(user.banner.url)

    return embed


async def generate_profile_user_embed(interaction: discord.Interaction['NeonBot'], user: discord.User):
    user = await interaction.client.fetch_user(user.id)

    # noinspection PyUnresolvedReferences
    flags = [flag.name.title().replace('_', ' ') for flag in user.public_flags.all()]

    embed = Embed(user.mention, timestamp=datetime.now())
    embed.set_author(str(user), icon_url=user.display_avatar.url)
    embed.set_footer(str(user.id))
    embed.add_field(t('utility.profile.created'), format_dt(user.created_at, 'F'), inline=False)
    embed.add_field(t('utility.profile.badges'), '\n'.join(flags) if len(flags) > 0 else t('utility.profile.none'), inline=False)

    if user.display_avatar:
        embed.set_thumbnail(user.display_avatar.url)

    if user.banner:
        embed.set_image(user.banner.url)

    return embed


async def check_ip_online_socket(host: str, port: int, timeout: float = 5.0) -> bool:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )

        writer.close()
        await writer.wait_closed()

        return True

    except (asyncio.TimeoutError, ConnectionRefusedError, OSError, asyncio.CancelledError):
        return False
    except Exception as e:
        print(f"An unexpected error occurred while checking {host}:{port}: {e}")
        return False


def is_youtube_url(url):
    parsed = urllib.parse.urlparse(url.lower())
    youtube_hosts = ('youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com')
    return parsed.hostname in youtube_hosts


def clean_youtube_url(url):
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)

    # Extract video ID from v param or youtu.be path
    vid = params.get('v', [None])[0]
    if not vid:
        path_match = re.match(r'/([a-zA-Z0-9_-]{11})', parsed.path)
        vid = path_match.group(1) if path_match else None

    if not vid:
        return url

    # Clean only if both video ID and 'list' present
    has_list = 'list' in params
    if has_list:
        if parsed.hostname == 'youtu.be':
            return f"https://youtu.be/{vid}"
        else:
            return f"https://www.youtube.com/watch?v={vid}"
    return url


async def wait_until(func, poll_interval=0.05, timeout=None):
    start_time = time.monotonic()

    while not func():
        if timeout is not None and (time.monotonic() - start_time) > timeout:
            break

        await asyncio.sleep(poll_interval)


async def ensure_ctx(ctx: Union[commands.Context['NeonBot'], discord.Interaction['NeonBot']]):
    if isinstance(ctx, discord.Interaction):
        return await ctx.client.get_context(ctx)
    return ctx
