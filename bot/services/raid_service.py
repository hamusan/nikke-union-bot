from bot.core.database import session_scope
from bot.exceptions import (
    ActiveRaidNotFoundError,
    BossNotFoundError,
    InvalidBossHpError,
    InvalidBossNameError,
    InvalidBossNumberError,
    RaidAlreadyExistsError,
)
from bot.models.boss import Boss
from bot.models.raid import Raid
from bot.repositories import (
    BossRepository,
    RaidRepository,
)


class RaidService:
    """Raid・Boss管理のアプリケーション処理。"""

    BOSS_MIN_NUMBER = 1
    BOSS_MAX_NUMBER = 5

    def create_raid(
        self,
        name: str,
    ) -> Raid:
        """新しいRaidを作成し、現在開催中にする。"""

        normalized_name = name.strip()

        if not normalized_name:
            raise ValueError(
                "Raid name must not be empty."
            )

        with session_scope() as session:
            raid_repository = RaidRepository(session)

            existing = raid_repository.get_by_name(
                normalized_name
            )

            if existing is not None:
                raise RaidAlreadyExistsError(
                    f"Raid '{normalized_name}' already exists."
                )

            # 新しいRaidを開始したら、
            # 以前のRaidは終了扱いにする。
            raid_repository.deactivate_all()

            return raid_repository.create(
                normalized_name
            )

    def get_active_raid(self) -> Raid:
        """現在開催中のRaidを取得する。"""

        with session_scope() as session:
            raid_repository = RaidRepository(session)

            raid = raid_repository.get_active()

            if raid is None:
                raise ActiveRaidNotFoundError(
                    "Active Raid was not found."
                )

            return raid

    def set_boss(
        self,
        boss_no: int,
        name: str,
        max_hp: int,
    ) -> Boss:
        """現在のRaidにBossを登録・更新する。"""

        self._validate_boss_number(
            boss_no
        )

        normalized_name = name.strip()

        if not normalized_name:
            raise InvalidBossNameError(
                "Boss name must not be empty."
            )

        if max_hp <= 0:
            raise InvalidBossHpError(
                "Boss HP must be greater than zero."
            )

        with session_scope() as session:
            raid_repository = RaidRepository(session)
            boss_repository = BossRepository(session)

            raid = raid_repository.get_active()

            if raid is None:
                raise ActiveRaidNotFoundError(
                    "Active Raid was not found."
                )

            boss = boss_repository.get_by_raid_and_number(
                raid_id=raid.id,
                boss_no=boss_no,
            )

            if boss is None:
                return boss_repository.create(
                    raid_id=raid.id,
                    boss_no=boss_no,
                    name=normalized_name,
                    max_hp=max_hp,
                )

            return boss_repository.update_definition(
                boss=boss,
                name=normalized_name,
                max_hp=max_hp,
            )

    def set_current_hp(
        self,
        boss_no: int,
        current_hp: int,
    ) -> Boss:
        """現在のBoss残HPを変更する。"""

        self._validate_boss_number(
            boss_no
        )

        if current_hp < 0:
            raise InvalidBossHpError(
                "Boss HP must not be negative."
            )

        with session_scope() as session:
            raid_repository = RaidRepository(session)
            boss_repository = BossRepository(session)

            raid = raid_repository.get_active()

            if raid is None:
                raise ActiveRaidNotFoundError(
                    "Active Raid was not found."
                )

            boss = boss_repository.get_by_raid_and_number(
                raid_id=raid.id,
                boss_no=boss_no,
            )

            if boss is None:
                raise BossNotFoundError(
                    f"Boss {boss_no} was not found."
                )

            if current_hp > boss.max_hp:
                raise InvalidBossHpError(
                    "Current HP cannot exceed max HP."
                )

            return boss_repository.set_current_hp(
                boss=boss,
                current_hp=current_hp,
            )

    def list_bosses(self) -> list[Boss]:
        """現在開催中RaidのBoss一覧を取得する。"""

        with session_scope() as session:
            raid_repository = RaidRepository(session)
            boss_repository = BossRepository(session)

            raid = raid_repository.get_active()

            if raid is None:
                raise ActiveRaidNotFoundError(
                    "Active Raid was not found."
                )

            return boss_repository.list_by_raid_id(
                raid.id
            )

    def _validate_boss_number(
        self,
        boss_no: int,
    ) -> None:
        if not (
            self.BOSS_MIN_NUMBER
            <= boss_no
            <= self.BOSS_MAX_NUMBER
        ):
            raise InvalidBossNumberError(
                "Boss number must be between "
                f"{self.BOSS_MIN_NUMBER} and "
                f"{self.BOSS_MAX_NUMBER}."
            )