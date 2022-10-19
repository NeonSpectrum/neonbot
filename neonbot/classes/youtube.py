import re

from i18n import t

from neonbot import bot
from neonbot.classes.embed import Embed, EmbedChoices
from neonbot.classes.player import Player
from neonbot.classes.with_interaction import WithInteraction
from neonbot.classes.ytdl import ytdl
from neonbot.utils.constants import YOUTUBE_REGEX
from neonbot.utils.exceptions import YtdlError


class Youtube(WithInteraction):
    async def send_message(self, *args, **kwargs):
        await bot.send_response(self.interaction, *args, **kwargs)

    async def search_keyword(self, keyword: str):
        player = await Player.get_instance(self.interaction)

        try:
            data = await ytdl.extract_info(keyword, process=True)
        except YtdlError:
            await self.send_message(embed=Embed(t('music.no_songs_available')), ephemeral=True)
            return

        choice = (await EmbedChoices(self.interaction, ytdl.parse_choices(data)).build()).value

        if choice < 0:
            await self.interaction.delete_original_response()
            return

        info = data[choice]

        await self.send_message(embed=Embed(
            t('music.added_to_queue', queue=len(player.queue) + 1, title=info['title'], url=info['url'])
        ))

        player.add_to_queue(info, requested=self.interaction.user)

    async def search_url(self, url: str):
        if not re.search(YOUTUBE_REGEX, url):
            await self.send_message(embed=Embed(t('music.invalid_youtube_url')), ephemeral=True)
            return

        player = await Player.get_instance(self.interaction)

        await self.send_message(embed=Embed(t('music.fetching_youtube_url')))

        data = await ytdl.extract_info(url, process=False)

        if isinstance(data, list):
            await self.send_message(embed=Embed(t('music.added_multiple_to_queue', count=len(data))))
        elif isinstance(data, dict):
            await self.send_message(embed=Embed(
                t('music.added_to_queue', queue=len(player.queue) + 1, title=data['title'], url=data['url'])
            ))
        else:
            await self.send_message(embed=Embed(t('music.song_failed_to_load')))

        player.add_to_queue(data, requested=self.interaction.user)
