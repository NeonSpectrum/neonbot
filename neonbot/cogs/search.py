import json
import textwrap
from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord import app_commands
from discord.app_commands.models import Choice
from discord.ext import commands
from jikanpy import AioJikan
from i18n import t

from neonbot.discord_ui.embed import Embed, EmbedChoices, PaginationEmbed
from neonbot.core.google_auth import get_google_access_token
from neonbot.env import GOOGLE_CX, GOOGLE_API, DICTIONARY_API, PROXY, OPENWEATHERMAP_API
from neonbot.utils import log
from neonbot.utils.constants import ICONS
from neonbot.utils.exceptions import ApiError

if TYPE_CHECKING:
    from neonbot import NeonBot


class Search(commands.Cog):
    anime = app_commands.Group(name='anime', description='Searches for top, upcoming, or specific anime.')

    def __init__(self, bot: 'NeonBot') -> None:
        self.bot = bot

        with open('./neonbot/assets/lang.json', 'r') as f:
            self.lang_list = json.load(f)

        with open('./neonbot/assets/city.list.json', 'r', encoding='utf8') as f:
            self.city_list = json.load(f)

    @app_commands.command(name='joke')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def joke(self, interaction: discord.Interaction['NeonBot']) -> None:
        """Tells a random dad joke."""

        res = await self.bot.session.get('https://icanhazdadjoke.com', headers={'Accept': 'application/json'})
        data = await res.json()

        await interaction.response.send_message(embed=Embed(data['joke']))

    @app_commands.command(name='image')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def image(self, interaction: discord.Interaction['NeonBot'], keyword: str) -> None:
        """Searches for an image in Google Image."""

        res = await self.bot.session.get(
            'https://www.googleapis.com/customsearch/v1',
            params={
                'q': keyword,
                'num': 1,
                'searchType': 'image',
                'cx': GOOGLE_CX,
                'key': GOOGLE_API,
            },
        )
        image = await res.json()

        if image.get('error'):
            raise ApiError(image['error']['message'])

        embed = Embed()
        embed.set_author(
            name=t('search.google_images_for', keyword=keyword),
            icon_url=ICONS['google'],
        )
        embed.set_footer(text=t('search.searched_by', user=interaction.user), icon_url=interaction.user.display_avatar.url)
        embed.set_image(url=image['items'][0]['link'])

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='dictionary')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def dictionary(self, interaction: discord.Interaction['NeonBot'], word: str) -> None:
        """Searches for a word in Merriam Webster."""

        res = await self.bot.session.get(
            f'https://www.dictionaryapi.com/api/v3/references/sd4/json/{word}',
            params={'key': DICTIONARY_API},
        )

        try:
            data = await res.json()
        except aiohttp.ContentTypeError:
            error = await res.text()
            raise ApiError(error)

        if not data or not isinstance(data[0], dict):
            await interaction.response.send_message(
                embed=Embed(t('search.word_not_found')), ephemeral=True
            )
            return

        dictionary = data[0]
        prs = dictionary['hwi']['prs'][0] or dictionary['vrs'][0]['prs'][0]
        audio = prs['sound']['audio']

        if audio:
            url = f'https://media.merriam-webster.com/soundc11/{audio[0]}/{audio}.wav'
            res = await self.bot.session.get(url)

        term = dictionary['meta']['id']

        if ':' in term:
            term = term[0: term.rfind(':')]

        embed = Embed()
        embed.add_field(
            name=term,
            value=(f'*{prs["mw"]}*' if prs['mw'] else '') + '\n' + dictionary['shortdef'][0],
        )
        embed.set_author(
            name=t('search.dictionary_title'),
            icon_url=ICONS['merriam'],
        )
        embed.set_footer(text=t('search.searched_by', user=interaction.user), icon_url=interaction.user.display_avatar.url)

        if audio:
            content = await res.read()
            await interaction.response.send_message(
                embed=embed, file=discord.File(BytesIO(content), word + '.wav')
            )
        else:
            await interaction.response.send_message(embed=embed)

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

    @app_commands.command(name='lyrics')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def lyrics(self, interaction: discord.Interaction['NeonBot'], song: str) -> None:
        """Searches for a lyrics in AZLyrics."""

        res = await self.bot.session.get(
            'https://search.azlyrics.com/search.php',
            params={'q': song, 'x': '309dddb3dd4a2067f6332f8abc9c8dbe611be904305dc2c4d3cd0db59c783abd'},
        )
        html = await res.text()
        soup = BeautifulSoup(html, 'html.parser')
        links = [
            dict(title=link.find('b').get_text(), url=link.get('href'))
            for link in soup.select('td.visitedlyr > a')
            if '/lyrics/' in link.get('href')
        ]

        embed_choices = await EmbedChoices(interaction, links[:5]).build()
        choice = embed_choices.value

        if choice < 0:
            return

        try:
            res = await self.bot.session.get(links[choice]['url'], proxy=PROXY)
            html = await res.text()
            soup = BeautifulSoup(html, 'html.parser')
            div = soup.select('div.col-xs-12.col-lg-8.text-center')[0]
            title = div.select('b')[1].get_text()[1:-1]
            lyrics = div.select('div:nth-of-type(5)')[0].get_text().splitlines()
        except Exception:
            log.exception('There was an error parsing the url.')
            await interaction.response.send_message(
                embed=Embed(t('search.lyrics_error')), ephemeral=True
            )
        else:
            lines = []

            for i in range(0, len(lyrics), 25):
                line = lyrics[i: i + 25]
                while not line[-1]:
                    del line[-1]
                while not line[0]:
                    del line[0]
                lines.append('\n'.join(line))

            embeds = [Embed(line) for line in lines if line]

            pagination = PaginationEmbed(interaction, embeds=embeds)
            pagination.embed.set_author(name=title, icon_url=ICONS['music'])
            pagination.embed.set_footer(
                text=t('search.powered_by_azlyrics'),
                icon_url=ICONS['azlyrics'],
            )
            await pagination.build()

    @anime.command(name='search')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def anime_search(self, interaction: discord.Interaction['NeonBot'], keyword: str) -> None:
        """Searches for anime information."""

        jikan = AioJikan()
        results = (await jikan.search(search_type='anime', query=keyword))['data']
        await jikan.close()

        if not results:
            await interaction.response.send_message(
                embed=Embed(t('search.anime_not_found')), ephemeral=True
            )
            return

        anime = results[0]

        if anime['title_english'] and not anime['title_japanese']:
            title = anime['title_english']
        elif not anime['title_english'] and anime['title_japanese']:
            title = anime['title_japanese']
        else:
            title = f'{anime["title_english"]} ({anime["title_japanese"]})'

        from_date = anime['aired']['prop']['from']
        from_date = f'{from_date["year"]}/{from_date["month"]:02d}/{from_date["day"]:02d}'

        to_date = anime['aired']['prop']['to']
        if to_date:
            to_date = f'{to_date["year"]}/{to_date["month"]:02d}/{to_date["day"]:02d}'

        embed = Embed()
        embed.set_author(name=title, url=anime['url'])
        embed.set_thumbnail(url=anime['images']['jpg']['image_url'])
        embed.set_footer(
            text=t('search.powered_by_myanimelist'),
            icon_url=ICONS['myanimelist'],
        )
        embed.add_field(
            name=t('search.synopsis'),
            value=anime['synopsis'][:1000] + '...' if len(anime['synopsis']) > 1000 else anime['synopsis'],
            inline=False,
        )
        embed.add_field(t('search.episodes'), anime['episodes'])
        embed.add_field(t('search.rank'), anime['rank'])
        embed.add_field(t('search.status'), anime['status'])
        embed.add_field(t('search.aired'), f'{from_date} - {to_date or t("search.not_available")}')
        embed.add_field(t('search.genres'), ', '.join([genre['name'] for genre in anime['genres']]))

        await interaction.response.send_message(embed=embed)

    @anime.command(name='top')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def anime_top(self, interaction: discord.Interaction['NeonBot']) -> None:
        """Lists top anime."""

        jikan = AioJikan()
        result = (await jikan.top(type='anime'))['data']
        await jikan.close()

        embeds = []
        for i in range(0, len(result), 10):
            temp = []
            for index, value in enumerate(result[i: i + 10]):
                temp.append(f'`{i + index + 1}.` [{value["title"]}]({value["url"]})')
            embeds.append(Embed('\n'.join(temp)))

        pagination = PaginationEmbed(interaction, embeds=embeds)
        pagination.embed.title = t('search.top_50_anime')
        pagination.embed.set_footer(
            text=t('search.powered_by_myanimelist'),
            icon_url=ICONS['myanimelist'],
        )
        await pagination.build()

    @anime.command(name='upcoming')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def anime_upcoming(self, interaction: discord.Interaction['NeonBot']) -> None:
        """Lists upcoming anime."""

        jikan = AioJikan()
        result = (await jikan.seasons(extension='upcoming'))['data']
        await jikan.close()

        embeds = []
        for i in range(0, len(result), 10):
            temp = []
            for index, value in enumerate(result[i: i + 10], i):
                temp.append(f'`{index + 1}.` [{value["title"]}]({value["url"]})')
            embeds.append(Embed('\n'.join(temp)))

        pagination = PaginationEmbed(interaction, embeds=embeds)
        pagination.embed.title = t('search.upcoming_anime')
        pagination.embed.set_footer(
            text=t('search.powered_by_myanimelist'),
            icon_url=ICONS['myanimelist'],
        )
        await pagination.build()

    @app_commands.command(name='translate')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def translate(self, interaction: discord.Interaction['NeonBot'], lang: str, sentence: str) -> None:
        """Translates sentence based on language code given."""

        google_token = await get_google_access_token()

        query = {'q': sentence, 'format': 'text', 'target': lang}

        res = await self.bot.session.post(
            'https://translation.googleapis.com/language/translate/v2',
            data=query,
            headers={'Authorization': f'Bearer {google_token}'},
        )

        data = await res.json()

        if 'error' in data:
            if data['error']['code'] == 400 and data['error']['message'] == 'Invalid Value':
                await interaction.response.send_message(
                    embed=Embed(t('search.invalid_language')), ephemeral=True
                )
                return

            raise ApiError(data['error']['message'])

        source_lang = data['data']['translations'][0].get('detectedSourceLanguage', data.get('source'))
        target_lang = query['target']
        translated_text = data['data']['translations'][0]['translatedText']

        embed = Embed()
        embed.set_author(name=t('search.google_translate'), icon_url=ICONS['googletranslate'])
        embed.add_field(f'**{self.lang_list[source_lang]}**', sentence, inline=False)
        embed.add_field(f'**{self.lang_list[target_lang]}**', translated_text)

        await interaction.response.send_message(embed=embed)

    @translate.autocomplete(name='lang')
    async def lang_autocomplete(self, interaction: discord.Interaction['NeonBot'], current: str) -> list[Choice]:
        """Lists all language codes."""
        return [
            Choice(name=lang, value=code)
            for code, lang in self.lang_list.items()
            if lang.lower().startswith(current.lower())
        ][:25]



async def setup(bot: 'NeonBot') -> None:
    await bot.add_cog(Search(bot))
