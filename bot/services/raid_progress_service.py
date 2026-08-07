from __future__ import annotations

from bot.core.database import session_scope
from bot.repositories.raid_progress_repository import (
    RaidProgressRepository,
)
from bot.services.raid_progress import (
    RaidProgressState,
    next_phase,
    validate_phase,
)


class RaidProgressService:
    """Raid全体のPhase進行を管理する。"""

    def get_active(
        self,
    ) -> RaidProgressState | None:
        """現在のActive Raidの進行状態を取得する。"""

        with session_scope() as session:
            repository = (
                RaidProgressRepository(
                    session
                )
            )

            raid = repository.get_active()

            if raid is None:
                return None

            return self._to_state(
                raid
            )

    def get_by_id(
        self,
        raid_id: int,
    ) -> RaidProgressState | None:
        """Raid IDから進行状態を取得する。"""

        with session_scope() as session:
            repository = (
                RaidProgressRepository(
                    session
                )
            )

            raid = repository.get_by_id(
                raid_id
            )

            if raid is None:
                return None

            return self._to_state(
                raid
            )

    def set_phase(
        self,
        raid_id: int,
        phase_no: int,
    ) -> RaidProgressState:
        """
        Phaseを明示的に変更する。

        主に管理・テスト用途。
        """

        validate_phase(
            phase_no
        )

        with session_scope() as session:
            repository = (
                RaidProgressRepository(
                    session
                )
            )

            raid = repository.get_by_id(
                raid_id
            )

            if raid is None:
                raise ValueError(
                    (
                        "Raidが存在しません: "
                        f"raid_id={raid_id}"
                    )
                )

            repository.set_current_phase(
                raid=raid,
                phase_no=phase_no,
            )

            return self._to_state(
                raid
            )

    def advance_phase(
        self,
        raid_id: int,
    ) -> RaidProgressState:
        """
        Raidを次のPhaseへ進める。

        Phase 3の次は
        最終フェーズ到達状態となる。
        """

        with session_scope() as session:
            repository = (
                RaidProgressRepository(
                    session
                )
            )

            raid = repository.get_by_id(
                raid_id
            )

            if raid is None:
                raise ValueError(
                    (
                        "Raidが存在しません: "
                        f"raid_id={raid_id}"
                    )
                )

            new_phase = next_phase(
                raid.current_phase
            )

            repository.set_current_phase(
                raid=raid,
                phase_no=new_phase,
            )

            return self._to_state(
                raid
            )

    @staticmethod
    def _to_state(
        raid,
    ) -> RaidProgressState:
        return RaidProgressState(
            raid_id=raid.id,
            raid_name=raid.name,
            current_phase=(
                raid.current_phase
            ),
        )