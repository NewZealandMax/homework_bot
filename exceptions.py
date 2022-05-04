class TokenError(Exception):
    pass


class PracticumTokenError(TokenError):
    pass


class TelegramTokenError(TokenError):
    pass


class TelegramChatIDError(TokenError):
    pass


class NotDictError(TypeError):
    pass


class NotListError(TypeError):
    pass


class Response200Error(Exception):
    pass


class MessageError(Exception):
    pass
