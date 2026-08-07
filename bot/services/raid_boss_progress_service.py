from __future__ import annotations

from bot.core.database import session_scope
from bot.repositories.raid_boss_progress_repository import (
    RaidBossProgressRepository,
)
from bot.services.raid_boss_progress import (
    BOSS_SLOTS,
    BossProgressState,
    RaidPhaseProgressState,
)


class RaidBossProgressService:
    """Raid Bossの残HPを管理する。"""

    def get_active_phase(
        self,
    ) -> RaidPhaseProgressState | None:
        """
        Active Raidの現在Phase状態を取得する。
        """

        with session_scope() as session:
            repository = (
                RaidBossProgressRepository(
                    session
                )
            )

            raid = (
                repository.get_active_raid()
            )

            if raid is None:
                return None

            if raid.current_phase > 3:
                return RaidPhaseProgressState(
                    raid_id=raid.id,
                    raid_name=raid.name,
                    phase_no=raid.current_phase,
                    bosses=(),
                    missing_boss_nos=(),
                )

            return self._build_state(
                repository=repository,
                raid_id=raid.id,
                raid_name=raid.name,
                phase_no=(
                    raid.current_phase
                ),
            )

    def get_phase(
        self,
        raid_id: int,
        phase_no: int,
    ) -> RaidPhaseProgressState:
        """
        指定Raid・Phaseの状態を取得する。
        """

        if phase_no not in (
            1,
            2,
            3,
        ):
            raise ValueError(
                (
                    "攻略対象Phaseは"
                    "1～3です: "
                    f"{phase_no}"
                )
            )

        with session_scope() as session:
            repository = (
                RaidBossProgressRepository(
                    session
                )
            )

            raid = repository.get_raid(
                raid_id
            )

            if raid is None:
                raise ValueError(
                    (
                        "Raidが存在しません: "
                        f"raid_id={raid_id}"
                    )
                )

            return self._build_state(
                repository=repository,
                raid_id=raid.id,
                raid_name=raid.name,
                phase_no=phase_no,
            )

    def set_remaining_hp(
        self,
        raid_id: int,
        boss_no: int,
        phase_no: int,
        remaining_hp: int,
    ) -> BossProgressState:
        """
        Boss残HPを明示的に変更する。

        現時点では管理・テスト用途。
        """

        if boss_no not in BOSS_SLOTS:
            raise ValueError(
                (
                    "boss_noは1～5です: "
                    f"{boss_no}"
                )
            )

        if phase_no not in (
            1,
            2,
            3,
        ):
            raise ValueError(
                (
                    "phase_noは1～3です: "
                    f"{phase_no}"
                )
            )

        if remaining_hp < 0:
            raise ValueError(
                (
                    "remaining_hpは"
                    "0以上である必要があります。"
                )
            )

        with session_scope() as session:
            repository = (
                RaidBossProgressRepository(
                    session
                )
            )

            boss = (
                repository.get_boss_by_no(
                    raid_id=raid_id,
                    boss_no=boss_no,
                )
            )

            if boss is None:
                raise ValueError(
                    (
                        "Bossが設定されていません: "
                        f"raid_id={raid_id}, "
                        f"boss_no={boss_no}"
                    )
                )

            phase = repository.get_phase(
                boss_id=boss.id,
                phase_no=phase_no,
            )

            if phase is None:
                raise ValueError(
                    (
                        "BossPhaseが"
                        "設定されていません: "
                        f"boss_no={boss_no}, "
                        f"phase_no={phase_no}"
                    )
                )

            if (
                remaining_hp
                > phase.max_hp
            ):
                raise ValueError(
                    (
                        "remaining_hpはmax_hpを"
                        "超えられません: "
                        f"remaining={remaining_hp}, "
                        f"max={phase.max_hp}"
                    )
                )

            progress = (
                repository
                .get_or_create_progress(
                    phase
                )
            )

            repository.set_remaining_hp(
                progress=progress,
                remaining_hp=remaining_hp,
            )

            return BossProgressState(
                boss_id=boss.id,
                boss_no=boss.boss_no,
                boss_name=boss.name,
                boss_phase_id=phase.id,
                phase_no=phase.phase_no,
                max_hp=phase.max_hp,
                remaining_hp=(
                    progress.remaining_hp
                ),
            )

    def _build_state(
        self,
        repository: (
            RaidBossProgressRepository
        ),
        raid_id: int,
        raid_name: str,
        phase_no: int,
    ) -> RaidPhaseProgressState:
        bosses = repository.list_bosses(
            raid_id
        )

        states: list[
            BossProgressState
        ] = []

        configured_slots: set[
            int
        ] = set()

        for boss in bosses:
            if boss.boss_no not in BOSS_SLOTS:
                continue

            phase = repository.get_phase(
                boss_id=boss.id,
                phase_no=phase_no,
            )

            if phase is None:
                continue

            progress = (
                repository
                .get_or_create_progress(
                    phase
                )
            )

            configured_slots.add(
                boss.boss_no
            )

            states.append(
                BossProgressState(
                    boss_id=boss.id,
                    boss_no=boss.boss_no,
                    boss_name=boss.name,

                    boss_phase_id=phase.id,
                    phase_no=(
                        phase.phase_no
                    ),

                    max_hp=phase.max_hp,
                    remaining_hp=(
                        progress.remaining_hp
                    ),
                )
            )

        states.sort(
            key=lambda state: (
                state.boss_no
            )
        )

        missing = tuple(
            boss_no
            for boss_no in BOSS_SLOTS
            if boss_no
            not in configured_slots
        )

        return RaidPhaseProgressState(
            raid_id=raid_id,
            raid_name=raid_name,
            phase_no=phase_no,
            bosses=tuple(states),
            missing_boss_nos=missing,
        )