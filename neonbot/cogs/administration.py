import asyncio
import contextlib
import json
import logging
import sys
from io import StringIO
from typing import Generator, Optional, cast

import discord
from discord.ext import commands

from .. import bot, env
from ..classes import Embed, PaginationEmbed
from ..classes.converters import Required
from ..helpers.log import Log
from ..helpers.utils import convert_to_seconds, shell_exec

log = cast(Log, logging.getLogger(__name__))


@contextlib.contextmanager
def stdoutIO() -> Generator[StringIO, None, None]:
    old = sys.stdout
    stdout = StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old


class Administration(commands.Cog):
    """Administration commands that handles the management of the bot"""

    def __init__(self) -> None:
        self.session = bot.session
        self.bot = bot
        self.db = bot.db

    @commands.command()
    @commands.is_owner()
    async def eval(self, ctx: commands.Context, *, code: str) -> None:
        """Evaluates a line/s of python code. *BOT_OWNER"""

        guild_id = ctx.guild.id if ctx.guild else None

        env = {
            "bot": bot,
            "discord": discord,
            "commands": commands,
            "ctx": ctx,
            "players": bot.music,
            "player": bot.music.get(guild_id),
            "config": self.db.get_guild(guild_id).config,
            "rooms": bot.game,
            "room": bot.game.get(guild_id),
            "Embed": Embed,
            "send_to_all_owners": bot.send_to_all_owners,
            "p": print,
        }

        if code.startswith("```") and code.endswith("```"):
            code = "\n".join(code.splitlines()[1:-1])

        try:
            lines = "\n".join([f"  {i}" for i in code.splitlines()])

            with stdoutIO() as s:
                exec(f"async def x():\n{lines}\n", env)
                await eval("x()", env)
            output = s.getvalue()
        except Exception as e:
            output = str(e)
            await ctx.message.add_reaction("❌")
        else:
            await ctx.message.add_reaction("👌")

        if output:
            msg_array = [output[i : i + 1900] for i in range(0, len(output), 1900)]

            embeds = [Embed("```py\n" + msg.strip("\n") + "```") for msg in msg_array]

            pagination = PaginationEmbed(ctx, embeds=embeds)
            pagination.embed.set_author(
                name="Python Interpreter", icon_url="https://i.imgur.com/vzcWouB.png"
            )
            pagination.embed.set_footer(
                text=f"Executed by {ctx.author}", icon_url=ctx.author.avatar_url
            )
            await pagination.build()

    @commands.command()
    @commands.is_owner()
    async def generatelog(self, ctx: commands.Context) -> None:
        """Generates a link contains the content of debug.log. *BOT_OWNER"""

        if not env.str("PASTEBIN_API"):
            return await ctx.send(embed=Embed("Error. Pastebin API not found."))

        with open("./debug.log", "r") as f:
            text = f.read()
        res = await self.session.post(
            "https://pastebin.com/api/api_post.php",
            data={
                "api_dev_key": env.str("PASTEBIN_API"),
                "api_paste_code": text,
                "api_option": "paste",
                "api_paste_private": 1,
                "paste_expire_date": "10M",
            },
        )
        paste_link = await res.text()
        paste_id = paste_link.split("/")[-1]
        await ctx.send(
            embed=Embed(f"Generated pastebin: https://pastebin.com/raw/{paste_id}")
        )

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    @commands.guild_only()
    async def prune(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None,
        count: int = 1,
    ) -> None:
        """
        Deletes a number of messages. *MANAGE_MESSAGES
        If member is specified, it will delete message of that member.
        """

        config = self.db.get_guild(ctx.guild.id).config

        if config.deleteoncmd:
            await self.bot.delete_message(ctx.message)

        async for message in ctx.history(limit=1000 if member else count):
            if count <= 0:
                break

            if not member or message.author == member:
                await self.bot.delete_message(message)
                count -= 1

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def prefix(self, ctx: commands.Context, prefix: str) -> None:
        """Sets the prefix of the current server. *ADMINISTRATOR"""

        database = self.db.get_guild(ctx.guild.id)
        config = database.config
        config.prefix = prefix
        config = database.update().config
        await ctx.send(embed=Embed(f"Prefix is now set to {config.prefix}."))

    @commands.command()
    @commands.is_owner()
    async def setstatus(
        self,
        ctx: commands.Context,
        status: Required("online", "offline", "dnd", "idle"),  # type:ignore
    ) -> None:
        """Sets the status of the bot. *BOT_OWNER"""

        if status is False:
            return

        database = self.db.get_settings()
        settings = database.settings
        settings.status = status
        settings = database.update().settings

        await bot.change_presence(status=discord.Status[status])
        await ctx.send(embed=Embed(f"Status is now set to {settings.status}."))

    @commands.command()
    @commands.is_owner()
    async def setpresence(
        self,
        ctx: commands.Context,
        presence_type: Required("watching", "listening", "playing"),  # type:ignore
        *,
        name: str,
    ) -> None:
        """Sets the presence of the bot. *BOT_OWNER"""

        if presence_type is False:
            return

        database = self.db.get_settings()
        settings = database.settings
        settings.game.type = presence_type
        settings.game.name = name
        settings = database.update().settings

        await bot.change_presence(
            activity=discord.Activity(
                name=name, type=discord.ActivityType[settings.game.type]
            )
        )
        await ctx.send(
            embed=Embed(
                f"Presence is now set to {settings.game.type} {settings.game.name}."
            )
        )

    @commands.command()
    @commands.guild_only()
    async def alias(self, ctx: commands.Context, name: str, *, command: str) -> None:
        """
        Sets or updates an alias command.

        You must be the owner of the alias to update it.
        """

        database = self.db.get_guild(ctx.guild.id)
        aliases = database.config.aliases
        ids = [i for i, x in enumerate(aliases) if x.name == name]
        if any(ids):
            if int(aliases[ids[0]].owner) != ctx.author.id and await bot.is_owner(
                ctx.author
            ):
                return await ctx.send(
                    embed=Embed("You are not the owner of the alias."), delete_after=5
                )
            aliases[ids[0]].cmd = (
                command.replace(ctx.prefix, "{0}", 1)
                if command.startswith(ctx.prefix)
                else command
            )
        else:
            database.config.aliases.append(
                {"name": name, "cmd": command, "owner": ctx.author.id}
            )
        database.update()
        await ctx.send(
            embed=Embed(f"Message with exactly `{name}` will now execute `{command}`"),
            delete_after=10,
        )

    @commands.command()
    @commands.guild_only()
    async def deletealias(self, ctx: commands.Context, name: str) -> None:
        """
        Removes an alias command.

        You must be the owner of the alias to delete it.
        """

        database = self.db.get_guild(ctx.guild.id)
        aliases = database.config.aliases
        ids = [i for i, x in enumerate(aliases) if x.name == name]
        if not ids:
            return await ctx.send(embed=Embed("Alias doesn't exists."), delete_after=5)
        if int(aliases[ids[0]].owner) != ctx.author.id and await bot.is_owner(
            ctx.author
        ):
            return await ctx.send(
                embed=Embed("You are not the owner of the alias."), delete_after=5
            )
        del aliases[ids[0]]
        database.update()
        await ctx.send(embed=Embed(f"Alias`{name}` has been deleted."), delete_after=5)

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def deleteoncmd(self, ctx: commands.Context) -> None:
        """
        Enables/Disables delete on cmd. *BOT_OWNER

        If enabled, it will delete the command message of the user.
        """

        database = self.db.get_guild(ctx.guild.id)
        config = database.config
        config.deleteoncmd = not config.deleteoncmd
        config = database.update().config
        await ctx.send(
            embed=Embed(
                f"Delete on command is now set to {'enabled' if config.deleteoncmd else 'disabled'}."
            )
        )

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def voicetts(self, ctx: commands.Context) -> None:
        """
        Enables/Disables Voice TTS. *ADMINISTRATOR

        If enabled, the bot will send a tts message if someone joins/leaves a voice channel.

        Note: The message will be sent to the current channel this command last executed.
        """

        database = self.db.get_guild(ctx.guild.id)
        config = database.config
        config.channel.voicetts = (
            ctx.channel.id if config.channel.voicetts != ctx.channel.id else None
        )
        config = database.update().config

        if config.channel.voicetts:
            await ctx.send(embed=Embed("Voice TTS is now set to this channel."))
        else:
            await ctx.send(embed=Embed("Voice TTS is now disabled."))

    @commands.group(invoke_without_command=True)
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def logger(self, ctx: commands.Context) -> None:
        """
        Enables/Disables Logger. *ADMINISTRATOR
        """

        await ctx.send(embed=Embed("Incomplete command. <presence | message>"))

    @logger.command(name="presence")
    async def logger_presence(self, ctx: commands.Context) -> None:
        """
        Logs presence.

        If enabled, the bot will log the following:
            - If someone joins/leaves the guild.
            - If someone joins/leaves the voice channel.
            - If someone updates his/her status or presence.

        Note: The message will be sent to the current channel this command last executed.
        """
        database = self.db.get_guild(ctx.guild.id)
        config = database.config
        config.channel.log = (
            ctx.channel.id if config.channel.log != ctx.channel.id else None
        )
        config = database.update().config

        if config.channel.log:
            await ctx.send(embed=Embed("Logger Presence is now set to this channel."))
        else:
            await ctx.send(embed=Embed("Logger Presence is now disabled."))

    @logger.command(name="message")
    async def logger_message(self, ctx: commands.Context) -> None:
        """
        Logs messages.

        If enabled, the bot will log the following:
            - If someone delete his message.

        Note: The message will be sent to the current channel this command last executed.
        """
        database = self.db.get_guild(ctx.guild.id)
        config = database.config
        config.channel.msgdelete = (
            ctx.channel.id if config.channel.msgdelete != ctx.channel.id else None
        )
        config = database.update().config

        if config.channel.log:
            await ctx.send(embed=Embed("Logger Message is now set to this channel."))
        else:
            await ctx.send(embed=Embed("Logger Message is now disabled."))

    @commands.command()
    @commands.is_owner()
    async def update(self, ctx: commands.Context) -> None:
        """Updates the bot from github. *BOT_OWNER"""

        result = await shell_exec("git pull")

        embed = Embed()
        embed.set_author(
            name="Github Update",
            icon_url="https://cdn1.iconfinder.com/data/icons/social-media-vol-1-1/24/_github-512.png",
        )

        embed.description = result

        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def pipupdate(self, ctx: commands.Context) -> None:
        """Updates the package of the bot. *BOT_OWNER"""

        msg = await ctx.send(embed=Embed("Bot packages updating..."))

        embed = Embed()
        embed.set_author(name="Pipenv Update", icon_url="https://i.imgur.com/vzcWouB.png")

        embed.description = await self.bot.update_package('discord.py', 'youtube_dl')

        await msg.edit(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, *, ext: str = None) -> None:
        """Reloads a specific or all extension. *BOT_OWNER"""

        extensions = bot.extensions.keys() if ext is None else ["neonbot.cogs." + ext]

        try:
            for extension in extensions:
                bot.reload_extension(extension)
        except Exception as e:
            await ctx.send(embed=Embed(str(e)))
        else:
            msg = "Reloaded all modules" if ext is None else f"Reloaded module: {ext}."
            log.info(msg)
            await ctx.send(embed=Embed(msg))

    @commands.command()
    @commands.is_owner()
    async def restart(self, ctx: commands.Context) -> None:
        """Restarts bot. *BOT_OWNER"""

        bot.save_music()
        msg = await ctx.send(embed=Embed("Bot Restarting..."))
        with open("./tmp/restart_config.json", "w") as f:
            json.dump({"message_id": msg.id, "channel_id": ctx.channel.id}, f, indent=4)
        await bot.restart()

    @commands.command()
    @commands.has_guild_permissions(mute_members=True)
    async def servermute(self, ctx: commands.Context, member: discord.Member, time: str, *, reason: str = "") -> None:
        """Server mute with timer."""

        if member.voice is None:
            return await ctx.send(embed=Embed(f"{member} is not in voice."))

        if member.voice.mute is True:
            return await ctx.send(embed=Embed(f"{member} is already muted."))

        seconds = convert_to_seconds(time)

        await member.edit(mute=True, reason=reason)
        await ctx.send(embed=Embed(f"{member} has been muted for {seconds} seconds."))

        async def unmute():
            await asyncio.sleep(seconds)
            if member.voice.mute is True:
                await member.edit(mute=False, reason='Revert unmute')
                await ctx.send(embed=Embed(f"{member} is now unmuted."))

        self.bot.loop.create_task(unmute())

    @commands.command()
    @commands.has_guild_permissions(mute_members=True)
    async def serverunmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "") -> None:
        """Server unmute."""

        if member.voice is None:
            return await ctx.send(embed=Embed(f"{member} is not in voice."))

        if member.voice.mute is False:
            return await ctx.send(embed=Embed(f"{member} is already unmuted."))

        await member.edit(mute=False, reason=reason)
        await ctx.send(embed=Embed(f"{member} has been unmuted."))


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Administration())
