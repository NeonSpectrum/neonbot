import asyncio
import contextlib
import logging
import sys
from io import StringIO

import discord
from discord.ext import commands

from .. import bot, env
from ..cogs.game import rooms
from ..cogs.music import players
from ..helpers.utils import Embed, check_args, send_to_all_owners

log = logging.getLogger(__name__)


@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old


class Administration(commands.Cog):
    """Administration commands that handles the management of the bot"""

    def __init__(self, bot):
        self.bot = bot
        self.session = bot.session
        self.db = bot.db

    @commands.command()
    @commands.is_owner()
    async def eval(self, ctx, *, args):
        """Evaluates a line/s of python code. *BOT_OWNER"""

        env = {
            "bot": self.bot,
            "discord": discord,
            "commands": commands,
            "ctx": ctx,
            "players": players,
            "player": players[ctx.guild.id],
            "config": self.db.get_guild(ctx.guild.id).config,
            "rooms": rooms,
            "Embed": Embed,
            "send_to_all_owners": send_to_all_owners,
        }

        def cleanup(code):
            if code.startswith("```") and code.endswith("```"):
                return "\n".join(code.splitlines()[1:-1])
            return code

        try:
            code = cleanup(args).splitlines()
            lines = "\n".join([f"  {i}" for i in code])

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
            if len(output) > 1900:
                msg_array = [output[i : i + 1900] for i in range(0, len(output), 1900)]
            else:
                msg_array = [output]

            for msg in msg_array:
                await ctx.send(f"```py\n{msg}```")

    @commands.command()
    @commands.is_owner()
    async def generatelog(self, ctx):
        """Generates a link contains the content of debug.log. *BOT_OWNER"""

        if not env("PASTEBIN_API"):
            return await ctx.send(embed=Embed("Error. Pastebin API not found."))

        with open("./debug.log", "r") as f:
            text = f.read()
        res = await self.session.post(
            "https://pastebin.com/api/api_post.php",
            data={
                "api_dev_key": env("PASTEBIN_API"),
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
    @commands.is_owner()
    async def reload(self, ctx, *, args):
        """Reloads an extension. *BOT_OWNER"""

        try:
            self.bot.reload_extension("neonbot.cogs." + args)
        except Exception as e:
            await ctx.send(embed=Embed(str(e)))
        else:
            log.info(f"Reloaded module: {args}.")
            await ctx.send(embed=Embed(f"Reloaded module: `{args}`."))

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def prune(self, ctx, count: int = 1, member: discord.Member = None):
        """
        Deletes a number of messages. *MANAGE_MESSAGES
        If member is specified, it will delete message of that member.
        """

        config = self.db.get_guild(ctx.guild.id).config

        if config.deleteoncmd:
            count += 1

        limit = 100 if member else count

        def check(message):
            nonlocal count

            if count <= 0:
                return False

            count -= 1
            return not member or message.author.id == member.id

        await ctx.channel.purge(limit=limit, check=check)

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def prefix(self, ctx, arg):
        """Sets the prefix of the current server. *ADMINISTRATOR"""

        database = self.db.get_guild(ctx.guild.id)
        config = database.config
        config.prefix = arg
        config = database.update_config().config
        await ctx.send(embed=Embed(f"Prefix is now set to {config.prefix}."))

    @commands.command()
    @commands.is_owner()
    async def setstatus(self, ctx, arg):
        """Sets the status of the bot. *BOT_OWNER"""

        if not await check_args(ctx, arg, ["online", "offline", "dnd", "idle"]):
            return

        database = self.db.get_settings()
        settings = database.settings
        settings.status = arg
        settings = database.update_settings().settings

        await self.bot.change_presence(status=discord.Status[arg])
        await ctx.send(embed=Embed(f"Status is now set to {settings.prefix}."))

    @commands.command()
    @commands.is_owner()
    async def setpresence(self, ctx, presence_type, *, name):
        """Sets the presence of the bot. *BOT_OWNER"""

        if not await check_args(
            ctx, presence_type, ["watching", "listening", "playing"]
        ):
            return

        database = self.db.get_settings()
        settings = database.settings
        settings.game.type = presence_type
        settings.game.name = name
        settings = database.update_settings().settings

        await self.bot.change_presence(
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
    async def alias(self, ctx, name, *, command):
        """
        Sets or updates an alias command.

        You must be the owner of the alias to update it.
        """

        database = self.db.get_guild(ctx.guild.id)
        aliases = database.config.aliases
        ids = [i for i, x in enumerate(aliases) if x.name == name]
        if len(ids) > 0:
            if int(aliases[ids[0]].owner) != ctx.author.id and await bot.is_owner(
                ctx.author
            ):
                return await ctx.send(
                    embed=Embed(f"You are not the owner of the alias."), delete_after=5
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
        database.update_config()
        await ctx.send(
            embed=Embed(f"Message with exactly `{name}` will now execute `{command}`"),
            delete_after=10,
        )

    @commands.command()
    @commands.guild_only()
    async def deletealias(self, ctx, name):
        """
        Removes an alias command.

        You must be the owner of the alias to delete it.
        """

        database = self.db.get_guild(ctx.guild.id)
        aliases = database.config.aliases
        ids = [i for i, x in enumerate(aliases) if x.name == name]
        if len(ids) == 0:
            return await ctx.send(embed=Embed(f"Alias doesn't exists."), delete_after=5)
        if int(aliases[ids[0]].owner) != ctx.author.id and await bot.is_owner(
            ctx.author
        ):
            return await ctx.send(
                embed=Embed(f"You are not the owner of the alias."), delete_after=5
            )
        del aliases[ids[0]]
        database.update_config()
        await ctx.send(embed=Embed(f"Alias`{name}` has been deleted."), delete_after=5)

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def deleteoncmd(self, ctx):
        """
        Enables/Disables delete on cmd. *BOT_OWNER

        If enabled, it will delete the command message of the user.
        """

        database = self.db.get_guild(ctx.guild.id)
        config = database.config
        config.deleteoncmd = not config.deleteoncmd
        config = database.update_config().config
        await ctx.send(
            embed=Embed(
                f"Delete on command is now set to {'enabled' if config.deleteoncmd else 'disabled'}."
            )
        )

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def voicetts(self, ctx):
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
        config = database.update_config().config

        if config.channel.voicetts:
            await ctx.send(embed=Embed(f"Voice TTS is now set to this channel."))
        else:
            await ctx.send(embed=Embed(f"Voice TTS is now disabled."))

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def logger(self, ctx):
        """
        Enables/Disables Logger. *ADMINISTRATOR

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
        config = database.update_config().config

        if config.channel.log:
            await ctx.send(embed=Embed(f"Logger is now set to this channel."))
        else:
            await ctx.send(embed=Embed(f"Logger is now disabled."))

    @commands.command()
    @commands.is_owner()
    async def update(self, ctx):
        """Updates the bot from github."""
        
        process = await asyncio.create_subprocess_shell(
            "git pull", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        result = stdout.decode().strip()

        embed = Embed()
        embed.set_author(
            name="Github Update",
            icon_url="https://cdn1.iconfinder.com/data/icons/social-media-vol-1-1/24/_github-512.png",
        )

        embed.description = result

        await ctx.send(embed=embed)

        if "Updating" in result:
            self.bot.save_music()
            await self.bot.restart()

    @commands.command()
    @commands.is_owner()
    async def restart(self, ctx):
        """Restarts bot."""
        
        await self.bot.restart()


def setup(bot):
    bot.add_cog(Administration(bot))
