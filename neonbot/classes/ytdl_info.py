from datetime import datetime
from os import path

from neonbot.utils.constants import YOUTUBE_DOWNLOADS_DIR
from neonbot.utils.functions import format_seconds


class YtdlInfo:
    def __init__(self, result):
        self.result = result

    @property
    def is_playlist(self):
        return self.result.get('_type') == 'playlist'

    def is_downloaded(self, entry):
        return entry.get('id') and path.exists(f'{YOUTUBE_DOWNLOADS_DIR}/{entry.get("id")}')

    def get_playlist_info(self):
        return dict(
            title=self.result.get('title'),
            url=self.result.get('webpage_url'),
            thumbnail=self.result.get('thumbnails')[-1]['url'] if len(self.result.get('thumbnails', [])) > 0 else None,
            uploader=self.result.get('uploader'),
        )

    def get_list(self):
        entries = self.result.get('entries', [])
        data = []

        for entry in entries:
            if not entry:
                continue

            # if self.is_downloaded(entry):
            #     data.append(self.format_detailed_result(entry))
            # else:
            #     data.append(self.format_simple_result(entry))
            data.append(self.format_detailed_result(entry))

        return data

    def get_track(self):
        if not self.result:
            return None

        # if self.is_downloaded(self.result):
        #     return self.format_detailed_result(self.result)

        # return self.format_simple_result(self.result)
        return self.format_detailed_result(self.result)

    def format_description(self, description: str) -> str:
        if not description:
            return description

        description_arr = description.split('\n')[:15]
        while len('\n'.join(description_arr)) > 1000:
            description_arr.pop()
        if len(description.split('\n')) != len(description_arr):
            description_arr.append('...')
        return '\n'.join(description_arr)

    def format_simple_result(self, entry: dict) -> dict:
        return dict(
            _type='url',
            ie_key='Youtube',
            id=entry.get('id'),
            title=entry.get('title', '*Not Available*'),
            duration=entry.get('duration'),
            url=entry.get('original_url'),
            is_live=entry.get('live_status') == 'is_live' or entry.get('is_live', False),
        )

    def format_detailed_result(self, entry: dict) -> dict:
        return dict(
            id=entry.get('id'),
            title=entry.get('title'),
            description=self.format_description(entry.get('description')),
            uploader=entry.get('uploader'),
            duration=entry.get('duration'),
            formatted_duration=format_seconds(entry.get('duration')) if entry.get('duration') else 'N/A',
            thumbnail=entry.get('thumbnail'),
            stream=entry.get('url') if 'videoplayback' in entry.get('url', '') else None,
            url=entry.get('original_url', entry.get('url')),
            is_live=entry.get('is_live'),
            view_count=f'{entry.get("view_count"):,}' if entry.get('view_count') else 'N/A',
            upload_date=datetime.strptime(entry.get('upload_date'), '%Y%m%d').strftime('%b %d, %Y')
            if entry.get('upload_date')
            else None,
        )
