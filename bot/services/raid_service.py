from bot.core.database import session_scope
from bot.exceptions import (
    ActiveRaidNotFoundError,
    BossNotFoundError,
    InvalidBossHpError,
    InvalidBossNameError,
    InvalidBossNumberError,
    InvalidRaidNameError,
    RaidAlreadyExistsError,
    BossPhaseAlreadyExistsError,
    BossPhaseNotFoundError,
    InvalidPhaseNumberError,
)
from bot.models.boss import Boss
from bot.models.raid import Raid
from bot.repositories import (
    BossRepository,
    RaidRepository,
    BossPhaseRepository,
)

from bot.models.boss_phase import BossPhase


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
            raise InvalidRaidNameError(
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
    
    def set_boss_phase(
        self,
        boss_no: int,
        phase_no: int,
        max_hp: int,
    ) -> BossPhase:
        """BossのPhaseと最大HPを登録・更新する。"""

        self._validate_boss_number(
            boss_no
        )

        if phase_no <= 0:
            raise InvalidPhaseNumberError(
                "Phase number must be greater than zero."
            )

        if max_hp <= 0:
            raise InvalidBossHpError(
                "Boss HP must be greater than zero."
            )

        with session_scope() as session:
            raid_repository = RaidRepository(
                session
            )
            boss_repository = BossRepository(
                session
            )
            phase_repository = BossPhaseRepository(
                session
            )

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

            same_hp_phase = (
                phase_repository.get_by_boss_and_max_hp(
                    boss_id=boss.id,
                    max_hp=max_hp,
                )
            )

            if (
                same_hp_phase is not None
                and same_hp_phase.phase_no != phase_no
            ):
                raise BossPhaseAlreadyExistsError(
                    f"Max HP {max_hp} is already assigned "
                    f"to Phase {same_hp_phase.phase_no}."
                )

            phase = (
                phase_repository.get_by_boss_and_phase(
                    boss_id=boss.id,
                    phase_no=phase_no,
                )
            )

            if phase is None:
                return phase_repository.create(
                    boss_id=boss.id,
                    phase_no=phase_no,
                    max_hp=max_hp,
                )

            return phase_repository.update_max_hp(
                phase=phase,
                max_hp=max_hp,
            )

    def resolve_boss_phase(
        self,
        boss_name: str,
        max_hp: int,
    ) -> BossPhase:
        """Boss名と最大HPからPhaseを判定する。"""

        normalized_boss_name = (
            boss_name.strip()
        )

        if not normalized_boss_name:
            raise BossNotFoundError(
                "Boss name must not be empty."
            )

        if max_hp <= 0:
            raise InvalidBossHpError(
                "Boss HP must be greater than zero."
            )

        with session_scope() as session:
            raid_repository = RaidRepository(
                session
            )
            boss_repository = BossRepository(
                session
            )
            phase_repository = BossPhaseRepository(
                session
            )

            raid = raid_repository.get_active()

            if raid is None:
                raise ActiveRaidNotFoundError(
                    "Active Raid was not found."
                )

            boss = boss_repository.get_by_raid_and_name(
                raid_id=raid.id,
                name=normalized_boss_name,
            )

            if boss is None:
                raise BossNotFoundError(
                    f"Boss '{normalized_boss_name}' "
                    "was not found."
                )

            phase = (
                phase_repository.get_by_boss_and_max_hp(
                    boss_id=boss.id,
                    max_hp=max_hp,
                )
            )

            if phase is None:
                raise BossPhaseNotFoundError(
                    (
                        f"Phase was not found for "
                        f"Boss '{boss.name}' "
                        f"and Max HP {max_hp}."
                    )
                )

            return phase

    def list_boss_phases(
        self,
        boss_no: int,
    ) -> list[BossPhase]:
        """BossのPhase一覧を取得する。"""

        self._validate_boss_number(
            boss_no
        )

        with session_scope() as session:
            raid_repository = RaidRepository(
                session
            )
            boss_repository = BossRepository(
                session
            )
            phase_repository = BossPhaseRepository(
                session
            )

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

            return phase_repository.list_by_boss_id(
                boss.id
            )