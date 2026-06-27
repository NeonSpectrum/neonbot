from neonbot.utils.exceptions import ApiError, ExchangeGiftNotRegistered


class TestApiError:
    def test_is_exception(self):
        assert issubclass(ApiError, Exception)

    def test_message(self):
        error = ApiError('test message')
        assert str(error) == 'test message'


class TestExchangeGiftNotRegistered:
    def test_is_exception(self):
        assert issubclass(ExchangeGiftNotRegistered, Exception)

    def test_default_message(self):
        error = ExchangeGiftNotRegistered()
        assert 'not registered' in str(error).lower()
