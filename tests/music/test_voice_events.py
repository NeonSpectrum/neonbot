from unittest.mock import MagicMock

from neonbot.music.voice_events import VoiceEvents


class TestVoiceEvents:
    def _make_events(self, **kwargs):
        member = MagicMock()
        member.display_name = 'TestUser'
        member.mention = '@TestUser'
        member.guild.default_role = MagicMock()

        defaults = dict(
            channel_before=MagicMock(),
            channel_after=MagicMock(),
            self_deaf_before=False, self_deaf_after=False,
            self_mute_before=False, self_mute_after=False,
            server_deafen_before=False, server_deafen_after=False,
            server_mute_before=False, server_mute_after=False,
            self_stream_before=False, self_stream_after=False,
            self_video_before=False, self_video_after=False,
        )
        defaults.update(kwargs)

        before = MagicMock()
        before.channel = defaults['channel_before']
        before.self_deaf = defaults['self_deaf_before']
        before.self_mute = defaults['self_mute_before']
        before.deaf = defaults['server_deafen_before']
        before.mute = defaults['server_mute_before']
        before.self_stream = defaults['self_stream_before']
        before.self_video = defaults['self_video_before']

        after = MagicMock()
        after.channel = defaults['channel_after']
        after.self_deaf = defaults['self_deaf_after']
        after.self_mute = defaults['self_mute_after']
        after.deaf = defaults['server_deafen_after']
        after.mute = defaults['server_mute_after']
        after.self_stream = defaults['self_stream_after']
        after.self_video = defaults['self_video_after']

        return VoiceEvents(member, before, after)

    def test_channel_changed(self):
        ch_before = MagicMock(name='Channel A')
        ch_after = MagicMock(name='Channel B')
        events = self._make_events(channel_before=ch_before, channel_after=ch_after)
        assert events.is_channel_changed is True

    def test_no_channel_change(self):
        ch = MagicMock(name='Same Channel')
        events = self._make_events(channel_before=ch, channel_after=ch)
        assert events.is_channel_changed is False

    def test_self_deafen_changed(self):
        events = self._make_events(self_deaf_before=False, self_deaf_after=True)
        assert events.is_self_deafen_changed is True

    def test_self_mute_changed(self):
        events = self._make_events(self_mute_before=False, self_mute_after=True)
        assert events.is_self_muted_changed is True

    def test_server_deafen_changed(self):
        events = self._make_events(server_deafen_before=False, server_deafen_after=True)
        assert events.is_server_deafen_changed is True

    def test_server_mute_changed(self):
        events = self._make_events(server_mute_before=False, server_mute_after=True)
        assert events.is_server_muted_changed is True

    def test_self_stream_changed(self):
        events = self._make_events(self_stream_before=False, self_stream_after=True)
        assert events.is_self_stream_changed is True

    def test_self_video_changed(self):
        events = self._make_events(self_video_before=False, self_video_after=True)
        assert events.is_self_video_changed is True

    def test_no_changes(self):
        ch = MagicMock(name='Same')
        events = self._make_events(channel_before=ch, channel_after=ch)
        assert events.is_channel_changed is False
        assert events.is_self_deafen_changed is False
        assert events.is_self_muted_changed is False

    def test_get_channel_changed_message(self):
        ch_before = MagicMock(name='Old')
        ch_before.name = 'Old Channel'
        ch_before.mention = '#old'
        ch_after = MagicMock(name='New')
        ch_after.name = 'New Channel'
        ch_after.mention = '#new'
        events = self._make_events(channel_before=ch_before, channel_after=ch_after)
        msg = events.get_channel_changed_message()
        assert msg is not None
