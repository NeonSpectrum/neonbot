from neonbot.models.music import MusicModel


class TestMusicModel:
    def test_fields(self):
        model = MusicModel(volume=100, repeat=0, shuffle=False, autoplay=False)
        assert model.volume == 100
        assert model.repeat == 0
        assert model.shuffle is False
        assert model.autoplay is False

    def test_optional_defaults(self):
        model = MusicModel(volume=50, repeat=1, shuffle=True, autoplay=True)
        assert model.channel_id is None
        assert model.last_channel_id is None
        assert model.autojoin_channel_id is None

    def test_optional_set(self):
        model = MusicModel(
            volume=80, repeat=2, shuffle=False, autoplay=False,
            channel_id=123, last_channel_id=456, autojoin_channel_id=789
        )
        assert model.channel_id == 123
        assert model.last_channel_id == 456
        assert model.autojoin_channel_id == 789
