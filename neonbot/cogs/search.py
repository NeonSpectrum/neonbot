import random
import textwrap
from datetime import datetime
from io import BytesIO

import discord
from addict import Dict
from bs4 import BeautifulSoup
from discord.ext import commands

from bot import env
from helpers.utils import Embed, PaginationEmbed, embed_choices


class Search(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = bot.session

    @commands.command()
    async def image(self, ctx, *, args):
        if not env("GOOGLE_CX") or not env("GOOGLE_API"):
            return await ctx.send(
                embed=Embed(description="Error. Google API not found.")
            )

        msg = await ctx.send(embed=Embed(description="Searching..."))
        res = await self.session.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "q": args,
                "num": 1,
                "searchType": "image",
                "cx": env("GOOGLE_CX"),
                "key": env("GOOGLE_API"),
            },
        )
        image = Dict(await res.json())

        embed = Embed()
        embed.set_author(
            name=f"Google Images for {args}", icon_url="http://i.imgur.com/G46fm8J.png"
        )
        embed.set_footer(text=f"Searched by {ctx.author}")
        embed.set_image(url=image["items"][0].link)

        await msg.delete()
        await ctx.send(embed=embed)

    @commands.command(aliases=["dict"])
    async def dictionary(self, ctx, *, args):
        if not env("DICTIONARY_API"):
            return await ctx.send(
                embed=Embed(description="Error. Dictionary API not found.")
            )

        msg = await ctx.send(embed=Embed(description="Searching..."))
        res = await self.session.get(
            f"https://www.dictionaryapi.com/api/v3/references/sd4/json/{args}",
            params={"key": env("DICTIONARY_API")},
        )
        json = await res.json()
        if not isinstance(json[0], dict):
            await msg.delete()
            return await ctx.send(
                embed=Embed(description="Word not found."), delete_after=5
            )

        dictionary = Dict(json[0])
        prs = dictionary.hwi.prs[0] or dictionary.vrs[0].prs[0]
        audio = prs.sound.audio
        if audio:
            url = f"https://media.merriam-webster.com/soundc11/{audio[0]}/{audio}.wav"
            res = await self.session.get(url)

        embed = Embed()
        embed.add_field(name=args, value=f"*{prs.mw}*" + "\n" + dictionary.shortdef[0])
        embed.set_author(
            name="Merriam-Webster Dictionary",
            icon_url="https://dictionaryapi.com/images/MWLogo.png",
        )
        embed.set_footer(
            text=f"Searched by {ctx.author}", icon_url=ctx.author.avatar_url
        )

        await msg.delete()
        await ctx.send(embed=embed)
        if audio:
            content = await res.read()
            await ctx.send(file=discord.File(BytesIO(content), args + ".wav"))

    @commands.command()
    async def weather(self, ctx, *, loc):
        msg = await ctx.send(embed=Embed(description="Searching..."))
        res = await self.session.get(
            f"http://api.openweathermap.org/data/2.5/weather",
            params={
                "q": loc,
                "units": "metric",
                "appid": "a88701020436549755f42d7e4be71762",
            },
        )
        json = Dict(await res.json())

        await msg.delete()
        if json.cod != 200:
            return await ctx.send(
                embed=Embed(description="City not found."), delete_after=5
            )

        embed = Embed()
        embed.set_author(
            name=f"{json.sys.country} - {json.name}",
            url=f"https://openweathermap.org/city/{json.id}",
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
            name="☁ Weather",
            value=f"{json.weather[0].main} - {json.weather[0].description}",
            inline=False,
        )
        embed.add_field(
            name="🌡 Temperature",
            value=textwrap.dedent(
                f"""
                    Minimum Temperature: {json.main.temp_min}°C
                    Maximum Temperature: {json.main.temp_max}°C
                    Temperature: {json.main.temp}°C
                    """
            ),
            inline=False,
        )
        embed.add_field(
            name="💨 Wind",
            value=f"Speed: {json.wind.speed} m/s\nDegrees: {json.wind.deg or 'N/A'}°",
            inline=False,
        )
        embed.add_field(
            name="🌤 Sunrise",
            value=datetime.fromtimestamp(json.sys.sunrise).strftime(
                "%b %d, %Y %-I:%M:%S %p"
            ),
            inline=False,
        )
        embed.add_field(
            name="🌥 Sunset",
            value=datetime.fromtimestamp(json.sys.sunset).strftime(
                "%b %d, %Y %-I:%M:%S %p"
            ),
            inline=False,
        )
        embed.add_field(
            name="🔘 Coordinates",
            value=f"Longitude: {json.coord.lon}\nLatitude: {json.coord.lat}",
            inline=False,
        )
        embed.add_field(
            name="🎛 Pressure", value=f"{json.main.pressure} hpa", inline=False
        )
        embed.add_field(name="💧 Humidity", value=f"{json.main.humidity}%", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def lol(self, ctx, *, champion):
        loading_msg = await ctx.send(embed=Embed(description="Searching..."))
        res = await self.session.get(
            f"https://www.leaguespy.net/league-of-legends/champion/{champion}/stats"
        )
        await loading_msg.delete()
        if res.status == 404:
            return await ctx.send("Champion not found.")
        html = await res.text()
        soup = BeautifulSoup(html, "html.parser")

        skill_build = []
        item_build = []
        rune_build = [[], [], []]

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
        ]

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
        ]

        skill_grid = soup.find("div", "skill-grid").select("div.skill-grid__column")

        for row in skill_grid:
            for i, skill in enumerate(row.find_all("span")):
                if "active" in (skill.get("class") or []):
                    skill_build.append("qwer"[i])

        item_block = soup.find("div", "champ__buildBottomNew").select(".item-block")

        for row in item_block:
            arr = []
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
            {
                "name": soup.select(".champ__header__left__main > h2")[0].get_text(),
                "icon": soup.select(".champ__header__left__radial img")[0].get("src"),
                "role": soup.select(
                    ".stat-source > .stat-source__btn[active=true] > a"
                )[0]
                .get_text()
                .split(" ")[0],
                "role_icon": "https://www.leaguespy.net"
                + soup.select(".champ__header__left__radial > .overlay > img")[0].get(
                    "src"
                ),
                "win_rate": soup.select(".champ__header__left__main > .stats-bar")[0]
                .find("span")
                .get_text(),
                "ban_rate": soup.select(".champ__header__left__main > .stats-bar")[1]
                .find("span")
                .get_text(),
            }
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
        embed.add_field(name="Role", value=info.role, inline=False)
        embed.add_field(name="Win Rate", value=info.win_rate)
        embed.add_field(name="Ban Rate", value=info.ban_rate)
        embed.add_field(name="Weak Against", value=", ".join(weak_against))
        embed.add_field(name="Strong Against", value=", ".join(strong_against))
        embed.add_field(name="Skill Build", value=" > ".join(skill_build))
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
    async def lyrics(self, ctx, *, song):
        loading_msg = await ctx.send(embed=Embed(description="Searching..."))
        res = await self.session.get(
            "https://search.azlyrics.com/search.php", params={"q": song}
        )
        html = await res.text()
        soup = BeautifulSoup(html, "html.parser")
        links = [
            Dict({"title": link.find("b").get_text(), "url": link.get("href")})
            for link in soup.select("td.visitedlyr > a", limit=5)
        ]
        await loading_msg.delete()
        choice = await embed_choices(ctx, links)
        res = await self.session.get(links[choice].url, proxy=env("PROXY", None))
        html = await res.text()
        soup = BeautifulSoup(html, "html.parser")
        div = soup.select("div.col-xs-12.col-lg-8.text-center")[0]
        print(div.get_text())
        title = div.select("b")[0].get_text()
        lyrics = div.select("div:nth-of-type(5)")[0].get_text().splitlines()
        print(lyrics)

        lines = []

        for i in range(0, len(lyrics), 25):
            line = lyrics[i : i + 25]
            while line[-1]:
                del line[-1]
            while line[0]:
                del line[0]
            lines.append("\n".join(line))

        embeds = [Embed(description=line) for line in lines if line]

        embed = PaginationEmbed(array=embeds, authorized_users=[ctx.author.id])
        embed.set_author(name=title, icon_url="https://i.imgur.com/SBMH84I.png")
        embed.set_footer(
            text="Powered by AZLyrics",
            icon_url="https://www.azlyrics.com/az_logo_tr.png",
        )
        await embed.build(ctx)


def setup(bot):
    bot.add_cog(Search(bot))
