class YtdlError(Exception):
    pass


class ApiError(Exception):
    pass


class ExchangeGiftNotRegistered(Exception):
    def __init__(self):
        super().__init__('You are not registered in the exchange gift event.')


class PlayerError(Exception):
    pass
