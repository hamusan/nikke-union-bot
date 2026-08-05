class NikkeBotError(Exception):
    """Bot内で使用する独自例外の基底クラス。"""


class PlayerAlreadyExistsError(NikkeBotError):
    """Playerが既に登録されている場合のエラー。"""


class PlayerNotFoundError(NikkeBotError):
    """Playerが見つからない場合のエラー。"""