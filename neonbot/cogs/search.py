import json
import textwrap
from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands.models import Choice
from discord.ext import commands
from i18n import t

from neonbot.discord_ui.embed import Embed
from neonbot.env import OPENWEATHERMAP_API
from neonbot.utils.constants import ICONS
from neonbot.utils.exceptions import ApiError

if TYPE_CHECKING:
    from neonbot import NeonBot


class Search(commands.Cog):
    def __init__(self, bot: 'NeonBot') -> None:
        self.bot = bot

        with open('./neonbot/assets/city.list.json', 'r', encoding='utf8') as f:
            self.city_list = json.load(f)

    @app_commands.command(name='weather')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def weather(self, interaction: discord.Interaction['NeonBot'], location: str) -> None:
        """Searches for a weather forecast in Open Weather Map."""

        res = await self.bot.session.get(
            'https://api.openweathermap.org/data/2.5/weather',
            params={
                'q': location,
                'units': 'metric',
                'appid': OPENWEATHERMAP_API,
            },
        )
        data = await res.json()

        if data['cod'] == 401:
            raise ApiError(data['message'])

        if int(data['cod']) == 404:
            await interaction.response.send_message(
                embed=Embed(t('search.city_not_found')), ephemeral=True
            )
            return

        embed = Embed()
        embed.set_author(
            f'{data["sys"]["country"]} - {data["name"]}',
            f'https://openweathermap.org/city/{data["id"]}',
            icon_url=f'https://countryflagsapi.com/png/{data["sys"]["country"].lower()}',
        )
        embed.set_footer(
            text=t('search.powered_by_openweathermap'),
            icon_url=ICONS['openweather'],
        )
        embed.set_thumbnail(url=f'https://openweathermap.org/img/w/{data["weather"][0]["icon"]}.png')
        embed.add_field(
            t('search.weather'),
            f'{data["weather"][0]["main"]} - {data["weather"][0]["description"]}',
            inline=False,
        )
        embed.add_field(
            t('search.temperature'),
            textwrap.dedent(
                f"""
                {t('search.min_temperature', temp=data['main']['temp_min'])}
                {t('search.max_temperature', temp=data['main']['temp_max'])}
                {t('search.current_temperature', temp=data['main']['temp'])}
                """
            ),
            inline=False,
        )
        embed.add_field(
            t('search.wind'),
            f"{t('search.wind_speed', speed=data['wind']['speed'])}\n{t('search.wind_degrees', deg=data['wind']['deg'] or 'N/A')}",
            inline=False,
        )
        embed.add_field(
            t('search.sunrise'),
            datetime.fromtimestamp(data['sys']['sunrise']).strftime('%b %d, %Y %I:%M:%S %p'),
            inline=False,
        )
        embed.add_field(
            t('search.sunset'),
            datetime.fromtimestamp(data['sys']['sunset']).strftime('%b %d, %Y %I:%M:%S %p'),
            inline=False,
        )
        embed.add_field(
            t('search.coordinates'),
            f"{t('search.longitude', lon=data['coord']['lon'])}\n{t('search.latitude', lat=data['coord']['lat'])}",
            inline=False,
        )
        embed.add_field(t('search.pressure'), f'{data["main"]["pressure"]} hpa', inline=False)
        embed.add_field(t('search.humidity'), f'{data["main"]["humidity"]}%', inline=False)

        await interaction.response.send_message(embed=embed)

    @weather.autocomplete(name='location')
    async def location_autocomplete(self, interaction: discord.Interaction['NeonBot'], current: str):
        return [Choice(name=city, value=city) for city in self.city_list if city.lower().startswith(current.lower())][
            :25
        ]


async def setup(bot: 'NeonBot') -> None:
    await bot.add_cog(Search(bot))
