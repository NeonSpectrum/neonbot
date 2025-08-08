import re

from i18n import t

from neonbot.classes.embed import Embed
from neonbot.classes.player import Player
from neonbot.classes.with_interaction import WithInteraction
from neonbot.classes.ytdl import Ytdl
from neonbot.classes.ytmusic import YTMusic
from neonbot.utils.constants import YOUTUBE_REGEX
from neonbot.utils.exceptions import YtdlError


class Youtube(WithInteraction):
    async def search_keyword(self, keyword: str):
        player = await Player.get_instance(self.interaction)

        await self.send_message(embed=Embed(t('music.searching')))

        try:
            ytdl_info = await YTMusic().search(keyword)
            track = ytdl_info.get_track()

            if not track.get('id'):
                raise YtdlError()

            ytdl_info = await Ytdl().extract_info('https://www.youtube.com/watch?v=' + track.get('id'))
            data = ytdl_info.get_track()

        except (YtdlError, IndexError):
            await self.send_message(embed=Embed(t('music.no_songs_available')))
            return

        await self.send_message(
            embed=Embed(t('music.added_to_queue', queue=len(player.queue) + 1, title=data['title'], url=data['url']))
        )

        player.add_to_queue(data, requested=self.interaction.user)

    async def search_url(self, url: str):
        if not re.search(YOUTUBE_REGEX, url):
            await self.send_message(embed=Embed(t('music.invalid_youtube_url')), ephemeral=True)
            return

        player = await Player.get_instance(self.interaction)

        await self.send_message(embed=Embed(t('music.fetching_youtube_url')))

        try:
            ytdl_info = await Ytdl().extract_info(url)
        except YtdlError:
            await self.send_message(embed=Embed(t('music.no_songs_available')))
            return

        if ytdl_info.is_playlist:
            data, error = self.remove_invalid_videos(ytdl_info.get_list())
            playlist_info = ytdl_info.get_playlist_info()
            embed = Embed(
                t('music.added_multiple_to_queue', count=len(data)) + ' ' + t('music.added_failed', count=error)
            )
            embed.set_image(playlist_info.get('thumbnail'))
            embed.set_author(playlist_info.get('title'), playlist_info.get('url'))

            if playlist_info.get('uploader'):
                embed.set_footer('Uploaded by: ' + playlist_info.get('uploader'))
        else:
            data = ytdl_info.get_track()
            embed = Embed(t('music.added_to_queue', queue=len(player.queue) + 1, title=data['title'], url=data['url']))

        await self.send_message(embed=embed)
        player.add_to_queue(data, requested=self.interaction.user)

    def remove_invalid_videos(self, data):
        error = 0
        new_data = []

        for entry in data:
            if entry['title'] in ('[Private video]', '[Deleted video]'):
                error += 1
            else:
                new_data.append(entry)

        return new_data, error
