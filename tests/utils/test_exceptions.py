from neonbot.utils.exceptions import ApiError


class TestApiError:
    def test_is_exception(self):
        assert issubclass(ApiError, Exception)

    def test_message(self):
        error = ApiError('test message')
        assert str(error) == 'test message'
