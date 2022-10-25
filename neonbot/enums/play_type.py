from enum import Enum


class PlayType(Enum):
    SEARCH = 'YOUTUBE_SEARCH'
    YOUTUBE = 'YOUTUBE_URL'
    SPOTIFY = 'SPOTIFY_URL'

    def __eq__(self, other):
        return self.value == other
