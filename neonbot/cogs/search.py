import json
import logging
import textwrap
from datetime import datetime
from io import BytesIO
from typing import List, cast

import aiohttp
import discord
from addict import Dict
from bs4 import BeautifulSoup
from discord.ext import commands
from jikanpy import AioJikan

from neonbot.helpers.utils import shell_exec

from .. import bot, env
from ..classes import Embed, EmbedChoices, PaginationEmbed
from ..helpers.exceptions import ApiError
from ..helpers.log import Log

log = cast(Log, logging.getLogger(__name__))


class Search(commands.Cog):
    def __init__(self) -> None:
        self.bot = bot
        self.session = bot.session

        with open("./neonbot/assets/lang.json", "r") as f:
            self.lang_list = json.load(f)

    @commands.command()
    async def joke(self, ctx: commands.Context) -> None:
        """Tells a random dad joke."""

        res = await self.session.get(
            "https://icanhazdadjoke.com", headers={"Accept": "application/json"}
        )
        json = Dict(await res.json())

        await ctx.send(embed=Embed(json.joke))

    @commands.command()
    async def image(self, ctx: commands.Context, *, keyword: str) -> None:
        """Searches for an image in Google Image."""

        msg = await ctx.send(embed=Embed("Searching..."))

        res = await self.session.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "q": keyword,
                "num": 1,
                "searchType": "image",
                "cx": env.str("GOOGLE_CX"),
                "key": env.str("GOOGLE_API"),
            },
        )
        image = Dict(await res.json())

        await self.bot.delete_message(msg)

        if image.error:
            raise ApiError(image.error.message)

        embed = Embed()
        embed.set_author(
            name=f"Google Images for {keyword}",
            icon_url="http://i.imgur.com/G46fm8J.png",
        )
        embed.set_footer(
            text=f"Searched by {ctx.author}", icon_url=ctx.author.avatar_url
        )
        embed.set_image(url=image["items"][0].link)

        await ctx.send(embed=embed)

    @commands.command(aliases=["dict"])
    async def dictionary(self, ctx: commands.Context, *, word: str) -> None:
        """Searches for a word in Merriam Webster."""

        msg = await ctx.send(embed=Embed("Searching..."))
        res = await self.session.get(
            f"https://www.dictionaryapi.com/api/v3/references/sd4/json/{word}",
            params={"key": env.str("DICTIONARY_API")},
        )

        await self.bot.delete_message(msg)

        try:
            json = await res.json()
        except aiohttp.ContentTypeError:
            error = await res.text()
            raise ApiError(error)

        if not json or not isinstance(json[0], dict):
            return await ctx.send(embed=Embed("Word not found."), delete_after=5)

        dictionary = Dict(json[0])
        prs = dictionary.hwi.prs[0] or dictionary.vrs[0].prs[0]
        audio = prs.sound.audio
        if audio:
            url = f"https://media.merriam-webster.com/soundc11/{audio[0]}/{audio}.wav"
            res = await self.session.get(url)

        term = dictionary.meta.id

        if ":" in term:
            term = dictionary.meta.id[0 : dictionary.meta.id.rfind(":")]

        embed = Embed()
        embed.add_field(
            name=term,
            value=(f"*{prs.mw}*" if prs.mw else "") + "\n" + dictionary.shortdef[0],
        )
        embed.set_author(
            name="Merriam-Webster Dictionary",
            icon_url="https://dictionaryapi.com/images/MWLogo.png",
        )
        embed.set_footer(
            text=f"Searched by {ctx.author}", icon_url=ctx.author.avatar_url
        )

        await self.bot.delete_message(msg)
        await ctx.send(embed=embed)
        if audio:
            content = await res.read()
            await ctx.send(file=discord.File(BytesIO(content), word + ".wav"))

    @commands.command()
    async def weather(self, ctx: commands.Context, *, location: str) -> None:
        """Searches for a weather forecast in Open Weather Map."""

        msg = await ctx.send(embed=Embed("Searching..."))
        res = await self.session.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params={
                "q": location,
                "units": "metric",
                "appid": "a88701020436549755f42d7e4be71762",
            },
        )
        json = Dict(await res.json())

        await self.bot.delete_message(msg)

        if json.cod == 401:
            raise ApiError(json.message)

        if int(json.cod) == 404:
            return await ctx.send(embed=Embed("City not found."), delete_after=5)

        embed = Embed()
        embed.set_author(
            f"{json.sys.country} - {json.name}",
            f"https://openweathermap.org/city/{json.id}",
            icon_url=f"https://www.countryflags.io/{json.sys.country.lower()}/flat/32.png",
        )
        embed.set_footer(
            text="Powered by OpenWeatherMap",
            icon_url="https://media.dragstone.com/content/icon-openweathermap-1.png",
        )
        embed.set_thumbnail(
            url=f"http://openweathermap.org/img/w/{json.weather[0].icon}.png"
        )
        embed.add_field(
            "☁ Weather",
            f"{json.weather[0].main} - {json.weather[0].description}",
            inline=False,
        )
        embed.add_field(
            "🌡 Temperature",
            textwrap.dedent(
                f"""
                Minimum Temperature: {json.main.temp_min}°C
                Maximum Temperature: {json.main.temp_max}°C
                Temperature: {json.main.temp}°C
                """
            ),
            inline=False,
        )
        embed.add_field(
            "💨 Wind",
            f"Speed: {json.wind.speed} m/s\nDegrees: {json.wind.deg or 'N/A'}°",
            inline=False,
        )
        embed.add_field(
            "🌤 Sunrise",
            datetime.fromtimestamp(json.sys.sunrise).strftime("%b %d, %Y %-I:%M:%S %p"),
            inline=False,
        )
        embed.add_field(
            "🌥 Sunset",
            datetime.fromtimestamp(json.sys.sunset).strftime("%b %d, %Y %-I:%M:%S %p"),
            inline=False,
        )
        embed.add_field(
            "🔘 Coordinates",
            f"Longitude: {json.coord.lon}\nLatitude: {json.coord.lat}",
            inline=False,
        )
        embed.add_field("🎛 Pressure", f"{json.main.pressure} hpa", inline=False)
        embed.add_field("💧 Humidity", f"{json.main.humidity}%", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def lol(self, ctx: commands.Context, *, champion: str) -> None:
        """Searches for a champion guide in LeagueSpy."""

        loading_msg = await ctx.send(embed=Embed("Searching..."))
        res = await self.session.get(
            f"https://www.leaguespy.net/league-of-legends/champion/{champion}/stats"
        )
        await self.bot.delete_message(loading_msg)
        if res.status == 404:
            return await ctx.send(embed=Embed("Champion not found."))
        html = await res.text()
        soup = BeautifulSoup(html, "html.parser")

        skill_build = []
        item_build = []
        rune_build: List[list] = [[], [], []]

        champ_counter = soup.select("div.champ__counters")

        strong_against = [
            champ_counter[0]
            .select("div.champ__counters__radials__big > a > span")[0]
            .get_text(),
            champ_counter[0]
            .select("div.champ__counters__radials__small > a > span")[0]
            .get_text(),
            *[
                row.find("a").get_text().strip()
                for row in champ_counter[0].find_all("div", "ls-table__row")
            ],
        ] if len(champ_counter) > 0 else []

        weak_against = [
            champ_counter[1]
            .select("div.champ__counters__radials__big > a > span")[0]
            .get_text(),
            champ_counter[1]
            .select("div.champ__counters__radials__small > a > span")[0]
            .get_text(),
            *[
                row.find("a").get_text().strip()
                for row in champ_counter[1].find_all("div", "ls-table__row")
            ],
        ] if len(champ_counter) > 1 else []

        skill_grid = soup.find("div", "skill-grid").select("div.skill-grid__column")

        for row in skill_grid:
            for i, skill in enumerate(row.find_all("span")):
                if "active" in (skill.get("class") or []):
                    skill_build.append("qwer"[i])

        item_block = soup.find("div", "champ__buildBottomNew").select(".item-block")

        for row in item_block:
            arr: List[str] = []
            for top in row.select(".item-block__top"):
                arr += [
                    i.get_text() for i in top.select(".item-block__items > span > span")
                ]
            item_build.append(arr)

        rune_block = soup.find("div", "champ__buildLeftNew").select(
            "div.rune-block.rune-block--new"
        )[0]

        for rune in rune_block.select(".rune-block__primary > .rune-block__rune"):
            rune_build[0].append(rune.get("name"))
        for rune in rune_block.select(".rune-block__secondary > .rune-block__rune"):
            rune_build[1].append(rune.get("name"))
        for rune in rune_block.select(".rune-block__stat-shards .rune-block__shard"):
            rune_build[2].append(rune.get("title"))

        info = Dict(
            name=soup.select(".champ__header__left__main > h2")[0].get_text(),
            icon=soup.select(".champ__header__left__radial img")[0].get("src"),
            role=soup.select(".stat-source > .stat-source__btn[active=true] > a")[0]
            .get_text()
            .split(" ")[0],
            role_icon="https://www.leaguespy.net"
            + soup.select(".champ__header__left__radial > .overlay > img")[0].get(
                "src"
            ),
            win_rate=soup.select(".champ__header__left__main > .stats-bar")[0]
            .find("span")
            .get_text(),
            ban_rate=soup.select(".champ__header__left__main > .stats-bar")[1]
            .find("span")
            .get_text(),
        )

        embed = Embed()
        embed.set_author(
            name=info.name,
            icon_url=info.role_icon,
            url=f"https://www.leaguespy.net/league-of-legends/champion/{champion}/stats",
        )
        embed.set_thumbnail(url=info.icon)
        embed.set_footer(
            text="Powered by LeagueSpy",
            icon_url="https://www.leaguespy.net/images/favicon/favicon-32x32.png",
        )
        embed.add_field("Role", info.role, inline=False)
        embed.add_field("Win Rate", info.win_rate if info.win_rate else 'N/A')
        embed.add_field("Ban Rate", info.ban_rate if info.ban_rate else 'N/A')
        embed.add_field("Weak Against", ", ".join(weak_against) if weak_against else 'N/A')
        embed.add_field("Strong Against", ", ".join(strong_against) if strong_against else 'N/A')
        embed.add_field("Skill Build", " > ".join(skill_build) if skill_build else 'N/A')
        embed.add_field(
            name="Item Build",
            value=textwrap.dedent(
                f"""
                    **Starting Items:** {", ".join(item_build[0])}
                    **Boots:** {", ".join(item_build[1])}
                    **Core Items:** {", ".join(item_build[2])}
                    **Luxury Items:**  {", ".join(item_build[3])}
                """
            ),
        )
        embed.add_field(
            name="Rune Build",
            value=textwrap.dedent(
                f"""
                    **Primary:** {", ".join(rune_build[0])}
                    **Secondary:** {", ".join(rune_build[1])}
                    **Stat Shard:** {", ".join(rune_build[2])}
                    """
            ),
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def lyrics(self, ctx: commands.Context, *, song: str) -> None:
        """Searches for a lyrics in AZLyrics."""

        loading_msg = await ctx.send(embed=Embed("Searching..."))
        res = await self.session.get(
            "https://search.azlyrics.com/search.php", params={"q": song}
        )
        html = await res.text()
        soup = BeautifulSoup(html, "html.parser")
        links = [
            Dict(title=link.find("b").get_text(), url=link.get("href"))
            for link in soup.select("td.visitedlyr > a")
            if "/lyrics/" in link.get("href")
        ]
        await self.bot.delete_message(loading_msg)
        embed_choices = await EmbedChoices(ctx, links[:5]).build()
        choice = embed_choices.value

        if choice < 0:
            return

        try:
            res = await self.session.get(
                links[choice].url, proxy=env.str("PROXY", None)
            )
            html = await res.text()
            soup = BeautifulSoup(html, "html.parser")
            div = soup.select("div.col-xs-12.col-lg-8.text-center")[0]
            title = div.select("b")[0].get_text()
            lyrics = div.select("div:nth-of-type(5)")[0].get_text().splitlines()
        except Exception:
            log.exception("There was an error parsing the url.")
            await ctx.send(
                embed=Embed("There was error fetching the lyrics."), delete_after=5
            )
        else:
            lines = []

            for i in range(0, len(lyrics), 25):
                line = lyrics[i : i + 25]
                while not line[-1]:
                    del line[-1]
                while not line[0]:
                    del line[0]
                lines.append("\n".join(line))

            embeds = [Embed(line) for line in lines if line]

            pagination = PaginationEmbed(ctx, embeds=embeds)
            pagination.embed.set_author(
                name=title, icon_url="https://i.imgur.com/SBMH84I.png"
            )
            pagination.embed.set_footer(
                text="Powered by AZLyrics",
                icon_url="https://www.azlyrics.com/az_logo_tr.png",
            )
            await pagination.build()

    @commands.group(invoke_without_command=True)
    async def anime(self, ctx: commands.Context) -> None:
        """Searches for top, upcoming, or specific anime."""

        await ctx.send(embed=Embed("Incomplete command. <search | top | upcoming>"))

    @anime.command(name="search")
    async def anime_search(self, ctx: commands.Context, *, keyword: str) -> None:
        """Searches for anime information."""

        loading_msg = await ctx.send(embed=Embed("Searching..."))

        jikan = AioJikan()
        results = Dict(await jikan.search(search_type="anime", query=keyword)).results

        if not results:
            return await ctx.send(embed=Embed("Anime not found."), delete_after=5)

        anime = Dict(await jikan._get("anime", results[0].mal_id, None))
        await jikan.close()

        if anime.title_english and not anime.title_japanese:
            title = anime.title_english
        elif not anime.title_english and anime.title_japanese:
            title = anime.title_japanese
        else:
            title = f"{anime.title_english} ({anime.title_japanese})"

        embed = Embed()
        embed.set_author(name=title, url=anime.url)
        embed.set_thumbnail(url=anime.image_url)
        embed.set_footer(
            text="Powered by MyAnimeList",
            icon_url="https://cdn.myanimelist.net/images/faviconv5.ico",
        )
        embed.add_field(
            name="Synopsis",
            value=anime.synopsis[:1000] + "..."
            if len(anime.synopsis) > 1000
            else anime.synopsis,
            inline=False
        )
        embed.add_field("Episodes", anime.episodes)
        embed.add_field("Rank", anime.rank)
        embed.add_field("Status", anime.status)
        embed.add_field("Aired", anime.aired.string)
        embed.add_field("Genres", ", ".join([genre.name for genre in anime.genres]))

        await self.bot.delete_message(loading_msg)
        await ctx.send(embed=embed)

    @anime.command(name="top")
    async def anime_top(self, ctx: commands.Context) -> None:
        """Lists top anime."""

        jikan = AioJikan()
        result = Dict(await jikan.top(type="anime")).top
        await jikan.close()

        embeds = []
        for i in range(0, len(result), 10):
            temp = []
            for index, value in enumerate(result[i : i + 10]):
                temp.append(f"`{i+index+1}.` [{value.title}]({value.url})")
            embeds.append(Embed("\n".join(temp)))

        pagination = PaginationEmbed(ctx, embeds=embeds)
        pagination.embed.title = ":trophy: Top 50 Anime"
        pagination.embed.set_footer(
            text="Powered by MyAnimeList",
            icon_url="https://cdn.myanimelist.net/images/faviconv5.ico",
        )
        await pagination.build()

    @anime.command(name="upcoming")
    async def anime_upcoming(self, ctx: commands.Context) -> None:
        """Lists upcoming anime."""

        jikan = AioJikan()
        result = Dict(await jikan.season_later()).anime
        await jikan.close()

        embeds = []
        for i in range(0, len(result), 10):
            temp = []
            for index, value in enumerate(result[i : i + 10], i):
                temp.append(f"`{index+1}.` [{value.title}]({value.url})")
            embeds.append(Embed("\n".join(temp)))

        pagination = PaginationEmbed(ctx, embeds=embeds)
        pagination.embed.title = ":clock3: Upcoming Anime"
        pagination.embed.set_footer(
            text="Powered by MyAnimeList",
            icon_url="https://cdn.myanimelist.net/images/faviconv5.ico",
        )
        await pagination.build()

    @commands.command(aliases=["trans"])
    async def translate(
        self, ctx: commands.Context, lang: str, *, sentence: str
    ) -> None:
        """Translates sentence based on language code given."""

        google_token = shell_exec("gcloud auth application-default print-access-token")

        data = {"q": sentence, "format": "text"}

        lang = lang.split(">")

        if len(lang) > 1:
            data["source"] = lang[0]
            data["target"] = lang[1]
        else:
            data["target"] = lang[0]

        res = await self.session.get(
            "https://translation.googleapis.com/language/translate/v2",
            data=data,
            headers={"Authorization": f"Bearer {google_token}"}
        )

        json = Dict(await res.json())

        if "error" in json:
            raise ApiError("There was an issue translating this text.")

        if json.message:
            return await ctx.send(embed=Embed(json.message), delete_after=5)

        source_lang = json.data.translations[0].get("detectedSourceLanguage", data["source"])
        target_lang = data["target"]
        translated_text = json.data.translations[0].translatedText

        await ctx.send(
            embed=Embed(
                title=f"Translated from `{source_lang}` to `{target_lang}`",
                description=f"`{sentence}` → `{translated_text}`",
            )
        )

    @commands.command()
    async def langlist(self, ctx: commands.Context) -> None:
        """Lists all language codes."""

        items = list(self.lang_list.items())

        embeds = []
        for i in range(0, len(items), 25):
            temp = []
            for code, lang in items[i : i + 25]:
                temp.append(f"`{code}` → `{lang}`")
            embeds.append(Embed("\n".join(temp)))

        pagination = PaginationEmbed(ctx, embeds=embeds)
        pagination.embed.title = ":blue_book: Language Code List"
        await pagination.build()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Search())
