from datetime import datetime

from neonbot.utils.functions import format_seconds


class YtdlInfo:
    def __init__(self, result):
        self.result = result

    @property
    def is_playlist(self):
        return self.result.get('_type') == 'playlist'

    def get_playlist_info(self):
        return dict(
            title=self.result.get('title'),
            url=self.result.get('webpage_url'),
            thumbnail=self.result.get('thumbnails')[-1]['url'] if len(self.result.get('thumbnails', [])) > 0 else None,
            uploader=self.result.get('uploader')
        )

    def get_list(self, detailed: bool = False):
        entries = self.result.get('entries', [])

        if detailed:
            return [self.format_detailed_result(entry) for entry in entries if entry]

        return [self.format_simple_result(entry) for entry in entries if entry]

    def get_track(self, detailed: bool = False):
        if not self.result:
            return None

        if detailed:
            return self.format_detailed_result(self.result)

        return self.format_simple_result(self.result)

    def format_description(self, description: str) -> str:
        description_arr = description.split("\n")[:15]
        while len("\n".join(description_arr)) > 1000:
            description_arr.pop()
        if len(description.split("\n")) != len(description_arr):
            description_arr.append("...")
        return "\n".join(description_arr)

    def format_simple_result(self, entry: dict) -> dict:
        return dict(
            _type='url',
            ie_key='Youtube',
            id=entry.get('id'),
            title=entry.get("title", "*Not Available*"),
            duration=entry.get("duration"),
            url='https://www.youtube.com/watch?v=' + entry.get('id')
        )

    def format_detailed_result(self, entry: dict) -> dict:
        return dict(
            id=entry.get('id'),
            title=entry.get('title'),
            description=self.format_description(entry.get('description')),
            uploader=entry.get('uploader'),
            duration=entry.get('duration'),
            formatted_duration=format_seconds(entry.get('duration')) if entry.get('duration') else "N/A",
            thumbnail=entry.get('thumbnail'),
            stream=entry.get('url') if entry.get('is_live') else f"./tmp/youtube_dl/{entry.get('id')}",
            url=entry.get('webpage_url'),
            is_live=entry.get('is_live'),
            view_count=f"{entry.get('view_count'):,}",
            upload_date=datetime.strptime(entry.get('upload_date'), "%Y%m%d").strftime(
                "%b %d, %Y"
            ),
        )
