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

class RaidAlreadyExistsError(NikkeBotError):
    """同名のRaidが既に存在する場合のエラー。"""


class ActiveRaidNotFoundError(NikkeBotError):
    """現在開催中のRaidが存在しない場合のエラー。"""


class BossNotFoundError(NikkeBotError):
    """Bossが見つからない場合のエラー。"""


class InvalidBossNumberError(NikkeBotError):
    """Boss番号が不正な場合のエラー。"""


class InvalidBossHpError(NikkeBotError):
    """Boss HPが不正な場合のエラー."""


class InvalidBossNameError(NikkeBotError):
    """Boss名が不正な場合のエラー。"""

class InvalidRaidNameError(NikkeBotError):
    """Raid名が不正な場合のエラー。"""

class InvalidDamageError(NikkeBotError):
    """Damage値が不正な場合のエラー。"""


class TeamInactiveError(NikkeBotError):
    """使用しようとしたTeamが無効な場合のエラー。"""

    