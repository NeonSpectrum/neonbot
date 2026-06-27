from unittest.mock import MagicMock, patch

from neonbot.music.ytmusic import YTMusicHelper


class TestYTMusicHelper:
    def setup_method(self):
        self.bot = MagicMock()
        self.helper = YTMusicHelper(self.bot)

    @patch('neonbot.music.ytmusic._get_ytmusic')
    async def test_search_returns_video_id(self, mock_get):
        mock_client = MagicMock()
        mock_client.search.return_value = [{'videoId': 'abc123'}]
        mock_get.return_value = mock_client

        result = await self.helper.search('test song')
        assert result == 'abc123'

    @patch('neonbot.music.ytmusic._get_ytmusic')
    async def test_search_no_results(self, mock_get):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_get.return_value = mock_client

        result = await self.helper.search('nonexistent')
        assert result is None

    @patch('neonbot.music.ytmusic._get_ytmusic')
    async def test_search_error(self, mock_get):
        mock_get.side_effect = Exception('connection error')

        result = await self.helper.search('test')
        assert result is None

    @patch('neonbot.music.ytmusic._get_ytmusic')
    async def test_get_related_tracks(self, mock_get):
        mock_client = MagicMock()
        mock_client.get_watch_playlist.return_value = {
            'tracks': [
                {'videoId': 'v1', 'title': 'Track 1'},
                {'videoId': 'v2', 'title': 'Track 2'},
            ]
        }
        mock_get.return_value = mock_client

        result = await self.helper.get_related_tracks('v1')
        assert len(result) == 1
        assert result[0]['id'] == 'v2'

    @patch('neonbot.music.ytmusic._get_ytmusic')
    async def test_get_related_tracks_empty(self, mock_get):
        mock_client = MagicMock()
        mock_client.get_watch_playlist.return_value = {'tracks': []}
        mock_get.return_value = mock_client

        result = await self.helper.get_related_tracks('v1')
        assert result == []

    @patch('neonbot.music.ytmusic._get_ytmusic')
    async def test_like_song_success(self, mock_get):
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        await self.helper.like_song('video123')
        mock_client.rate_song.assert_called_once()

    @patch('neonbot.music.ytmusic._get_ytmusic')
    async def test_like_song_failure(self, mock_get):
        mock_client = MagicMock()
        mock_client.rate_song.side_effect = Exception('rate failed')
        mock_get.return_value = mock_client

        await self.helper.like_song('video123')

    @patch('neonbot.music.ytmusic._get_ytmusic')
    async def test_get_account_info(self, mock_get):
        mock_client = MagicMock()
        mock_client.get_account_info.return_value = {'id': 'user123'}
        mock_get.return_value = mock_client

        result = await self.helper.get_account_info()
        assert result == {'id': 'user123'}
