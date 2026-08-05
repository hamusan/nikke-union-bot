class NikkeBotError(Exception):
    """Bot内で使用する独自例外の基底クラス。"""


class PlayerAlreadyExistsError(NikkeBotError):
    """Playerが既に登録されている場合のエラー。"""


class PlayerNotFoundError(NikkeBotError):
    """Playerが見つからない場合のエラー。"""


class PlayerAlreadyInactiveError(NikkeBotError):
    """Playerがすでに無効になっている場合のエラー。"""

class TeamAlreadyExistsError(NikkeBotError):
    """同名のTeamが既に存在する場合のエラー。"""


class TeamNotFoundError(NikkeBotError):
    """Teamが見つからない場合のエラー。"""


class TeamAlreadyInactiveError(NikkeBotError):
    """Teamが既に無効になっている場合のエラー。"""


class InvalidTeamMemberCountError(NikkeBotError):
    """編成人数が正しくない場合のエラー。"""


class DuplicateCharacterError(NikkeBotError):
    """同じCharacterが編成内に重複している場合のエラー。"""


class InvalidCharacterNameError(NikkeBotError):
    """Character名が空など不正な場合のエラー。"""


class InvalidTeamNameError(NikkeBotError):
    """Team名が空など不正な場合のエラー。"""


class PlayerInactiveError(NikkeBotError):
    """Playerが無効になっている場合のエラー。"""