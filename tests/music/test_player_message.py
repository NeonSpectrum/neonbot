from unittest.mock import AsyncMock, MagicMock

from neonbot.music.player_message import PlayerMessageManager
from neonbot.music.enums import MessageType, Repeat


def _make_track(identifier='abc123', title='Test Track', uri='https://example.com', duration=180000, requester=789, source_name='youtube'):
    track = MagicMock()
    track.identifier = identifier
    track.title = title
    track.uri = uri
    track.duration = duration
    track.requester = requester
    track.source_name = source_name
    return track


class TestPlayerMessageManager:
    def setup_method(self):
        self.bot = MagicMock()
        self.bot.get_user.return_value = MagicMock(display_name='TestUser', display_avatar=MagicMock(url='https://example.com/avatar.png'))
        self.messager = PlayerMessageManager(self.bot, guild_id=456)

    def _setup_player(self):
        player = MagicMock()
        player.shuffle = False
        player.loop = Repeat.OFF.value
        player.autoplay = False
        player.track_list = []
        player.current_queue = 0
        self.bot.get_player_instance.return_value = player
        return player

    def test_get_footer(self):
        self._setup_player()
        track = _make_track()
        footer = self.messager.get_footer(track)
        assert len(footer) == 5
        assert footer[0] == 'TestUser'

    def test_get_track_embed(self):
        self._setup_player()
        track = _make_track()
        embed = self.messager.get_track_embed(track)
        assert embed.title == 'Test Track'
        assert embed.url == 'https://example.com'

    def test_get_playing_embed(self):
        player = self._setup_player()
        player.track_list = [_make_track()]
        track = _make_track()
        embed = self.messager.get_playing_embed(track)
        assert embed.title == 'Test Track'

    def test_get_finished_embed_compact(self):
        self._setup_player()
        track = _make_track()
        embed = self.messager.get_finished_embed(track, compact=True)
        assert 'Test Track' in embed.description

    def test_get_finished_embed_full(self):
        player = self._setup_player()
        player.track_list = [_make_track()]
        track = _make_track()
        embed = self.messager.get_finished_embed(track, compact=False)
        assert embed.title == 'Test Track'

    async def test_send_message(self):
        self._setup_player()
        self.messager.channel = MagicMock()
        self.messager.channel.send = AsyncMock(return_value=MagicMock())
        data = MagicMock()
        data.track = _make_track()

        await self.messager.send_message(data)

        assert len(self.messager.data) == 1
        self.messager.channel.send.assert_called_once()

    def test_clear(self):
        self.messager.data = [MagicMock(), MagicMock()]
        self.messager.clear()
        assert len(self.messager.data) == 0

    def test_get_latest_message(self):
        pm1 = MagicMock()
        pm1.type = MessageType.PLAYING
        pm2 = MagicMock()
        pm2.type = MessageType.FINISHED
        self.messager.data = [pm1, pm2]

        result = self.messager.get_latest_message(MessageType.FINISHED)
        assert result is pm2

    def test_get_latest_message_none(self):
        self.messager.data = []
        result = self.messager.get_latest_message(MessageType.PLAYING)
        assert result is None
