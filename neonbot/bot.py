import asyncio
import json
import logging
import os
import re
import shutil
import sys
from glob import glob
from os import path
from time import time
from typing import Any, Callable, List, Tuple, Union, cast, Optional

import aioschedule as schedule
import discord
import psutil
from aiohttp import ClientSession, ClientTimeout
from discord.ext import commands
from discord.utils import oauth_url

from neonbot.helpers.utils import shell_exec
from . import __title__, __version__
from .classes.embed import Embed
from .database import Database
from .env import env
from .helpers.constants import LOGO, PERMISSIONS
from .helpers.log import Log, cprint

log = cast(Log, logging.getLogger(__name__))


class Bot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=self.get_command_prefix(), intents=discord.Intents.all()
        )

        self.start_message()

        self.env = env
        self.db = Database()
        self.default_prefix = env.str("DEFAULT_PREFIX", ".")
        self.owner_ids = set(env.list("OWNER_IDS", [], subcast=int))

        self.status, self.activity = self.get_presence()
        self.session = ClientSession(loop=self.loop, timeout=ClientTimeout(total=30))
        self.user_agent = f"NeonBot v{__version__}"

        self.app_info: Optional[discord.AppInfo] = None
        self.set_storage()
        self.load_music()

        schedule.every().day.at("06:00").do(self.auto_update_ytdl)
        self.loop.create_task(self.run_scheduler())
        # self.clear_youtube_dl_cache()

    def set_storage(self) -> None:
        self.commands_executed: List[str] = []
        self.game = {}
        self.music = {}
        self.chatbot = {}
        self._music_cache = {}

    def load_music(self) -> None:
        file = "./tmp/music.json"
        if path.exists(file):
            with open(file, "r") as f:
                self._music_cache = json.load(f)
            os.remove(file)

    def save_music(self) -> None:
        file = "./tmp/music.json"
        with open(file, "w") as f:
            cache = {}
            for key, player in self.music.items():
                cache[key] = {
                    "current_queue": player.current_queue,
                    "queue": [
                        {**queue, "requested": queue.requested.id}
                        for queue in player.queue
                    ],
                }
            json.dump(cache, f, indent=4)

    def start_message(self) -> None:
        cprint(LOGO, "blue")
        log.info(f"Starting {__title__} v{__version__}")

    def get_presence(self) -> Tuple[discord.Status, discord.Activity]:
        settings = self.db.get_settings()
        activity_type = settings.get('game')['type'].lower()
        activity_name = settings.get('game')['name']
        status = settings.get('status')

        return (
            discord.Status[status],
            discord.Activity(
                name=activity_name, type=discord.ActivityType[activity_type]
            ),
        )

    async def fetch_app_info(self) -> None:
        if not self.app_info:
            self.app_info = await self.application_info()

    def get_command_prefix(self) -> Union[Callable, str]:
        return (
            lambda _, message: self.db.get_guild(message.guild.id).get('prefix')
            if message.guild
            else self.default_prefix
        )

    def load_cogs(self) -> None:
        files = sorted(glob("neonbot/cogs/[!_]*.py"))
        extensions = list(map(lambda x: re.split(r"[/.]", x)[-2], files))
        start_time = time()

        print(file=sys.stderr)

        for extension in extensions:
            log.info(f"Loading {extension} cog...")
            self.load_extension("neonbot.cogs." + extension)

        print(file=sys.stderr)

        log.info(f"Loaded {len(extensions)} cogs after {(time() - start_time):.2f}s")

    async def update_package(self, *packages) -> str:
        log.info(f"Executing update package...")

        result = await shell_exec(f"pipenv update {' '.join(packages)}")

        log.info(f"\n{result}\n")

        return result.split("\n")[-1]

    async def close(self) -> None:
        await asyncio.gather(
            *[self.music[key].reset() for key in self.music],
            self.session.close(),
            return_exceptions=True
        )
        await super().close()

    async def restart(self) -> None:
        await self.close()
        try:
            p = psutil.Process(os.getpid())
            for handler in p.open_files() + p.connections():
                os.close(handler.fd)
        except Exception as e:
            log.exception(e)
        else:
            python = sys.executable
            os.execl(python, python, *sys.argv)

    async def send_restart_message(self) -> None:
        file = "./tmp/restart_config.json"
        if path.exists(file):
            with open(file, "r") as f:
                data = json.load(f)
            os.remove(file)

            channel = self.get_channel(data.channel_id)
            try:
                message = await channel.fetch_message(data.message_id)
            except discord.NotFound:
                pass
            else:
                await self.delete_message(message)
            await channel.send(embed=Embed("Bot Restarted."), delete_after=10)

    async def send_invite_link(self, channel: discord.DMChannel) -> None:
        with channel.typing():
            url = oauth_url(
                self.app_info.id,
                permissions=discord.Permissions(permissions=PERMISSIONS),
                scopes=('bot', 'applications.commands')
            )
            await channel.send(f"Bot invite link: {url}")
            log.info(f"Sent an invite link to: {channel.recipient}")

    async def send_to_all_owners(
        self, *args: Any, excluded: list = [], **kwargs: Any
    ) -> None:
        for owner in filter(lambda x: x not in excluded, self.owner_ids):
            await self.get_user(owner).send(*args, **kwargs)

    async def send_to_owner(
        self, *args: Any, sender: int = None, **kwargs: Any
    ) -> None:
        if sender != self.app_info.owner.id:
            await self.get_user(self.app_info.owner.id).send(*args, **kwargs)

    async def edit_message(self, message: Union[discord.Message, None], **kwargs) -> None:
        if message is None:
            return

        try:
            await message.edit(**kwargs)
        except discord.NotFound:
            pass

    async def delete_message(self, *messages: Union[discord.Message, None]) -> None:
        await asyncio.gather(
            *[message.delete() for message in messages if message is not None],
            return_exceptions=True
        )

    async def auto_update_ytdl(self) -> None:
        response = await shell_exec("yt-dlp -U")

        if "up to date" in response:
            return

        response = await self.update_package("yt-dlp")

        if "Successfully installed yt-dlp" in response:
            await self.restart()

    async def run_scheduler(self) -> None:
        while True:
            await schedule.run_pending()
            await asyncio.sleep(1)

    def clear_youtube_dl_cache(self) -> None:
        try:
            shutil.rmtree("./tmp/youtube_dl")
        except:
            pass

    def run(self) -> None:
        self.load_cogs()
        super().run(env.str("TOKEN"))
