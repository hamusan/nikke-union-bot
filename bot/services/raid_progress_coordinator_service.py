from __future__ import annotations

from dataclasses import dataclass

from bot.services.raid_boss_progress import (
    BossProgressState,
)
from bot.services.raid_boss_progress_service import (
    RaidBossProgressService,
)
from bot.services.raid_progress import (
    FINAL_REACHED_PHASE,
    decide_phase_transition,
)
from bot.services.raid_progress_service import (
    RaidProgressService,
)


@dataclass(
    frozen=True
)
class RaidPhaseAdvanceResult:
    """
    Phase進行判定の結果。
    """

    raid_id: int

    previous_phase: int
    current_phase: int

    advanced: bool
    final_reached: bool

    reason: str

    defeated_count: int

    missing_boss_nos: tuple[
        int,
        ...
    ]


@dataclass(
    frozen=True
)
class RaidBossProgressUpdateResult:
    """
    Boss残HP更新 + Phase判定結果。
    """

    boss: BossProgressState

    transition: (
        RaidPhaseAdvanceResult
    )


class RaidProgressCoordinatorService:
    """
    Boss残HPとRaid Phase進行を
    まとめて調整するService。

    DiscordやOCRには依存しない。
    """

    def __init__(
        self,
    ) -> None:
        self._raid_service = (
            RaidProgressService()
        )

        self._boss_service = (
            RaidBossProgressService()
        )

    def evaluate_and_advance(
        self,
        raid_id: int,
    ) -> RaidPhaseAdvanceResult:
        """
        現在Phaseを確認し、

        Boss #1～#5が全撃破なら
        次Phaseへ進める。
        """

        raid = (
            self._raid_service
            .get_by_id(
                raid_id
            )
        )

        if raid is None:
            raise ValueError(
                (
                    "Raidが存在しません: "
                    f"raid_id={raid_id}"
                )
            )

        previous_phase = (
            raid.current_phase
        )

        # --------------------------------
        # すでに最終フェーズ到達済み
        # --------------------------------

        if raid.final_reached:
            return RaidPhaseAdvanceResult(
                raid_id=raid.raid_id,

                previous_phase=(
                    previous_phase
                ),

                current_phase=(
                    previous_phase
                ),

                advanced=False,
                final_reached=True,

                reason="final_reached",

                defeated_count=5,

                missing_boss_nos=(),
            )

        # --------------------------------
        # 現在Phaseの5Boss状態
        # --------------------------------

        phase_state = (
            self._boss_service
            .get_phase(
                raid_id=raid_id,
                phase_no=(
                    previous_phase
                ),
            )
        )

        decision = (
            decide_phase_transition(
                current_phase=(
                    previous_phase
                ),

                all_bosses_configured=(
                    phase_state
                    .all_bosses_configured
                ),

                all_bosses_defeated=(
                    phase_state
                    .all_defeated
                ),
            )
        )

        # --------------------------------
        # まだ次Phaseへ進まない
        # --------------------------------

        if not decision.should_advance:
            return RaidPhaseAdvanceResult(
                raid_id=raid.raid_id,

                previous_phase=(
                    previous_phase
                ),

                current_phase=(
                    previous_phase
                ),

                advanced=False,
                final_reached=False,

                reason=decision.reason,

                defeated_count=(
                    phase_state
                    .defeated_count
                ),

                missing_boss_nos=(
                    phase_state
                    .missing_boss_nos
                ),
            )

        # --------------------------------
        # 次Phaseへ
        # --------------------------------

        new_raid = (
            self._raid_service
            .advance_phase(
                raid_id
            )
        )

        # --------------------------------
        # Phase 1 -> 2
        # Phase 2 -> 3
        #
        # 新PhaseのProgressを
        # 初期化しておく。
        # --------------------------------

        if (
            new_raid.current_phase
            <= 3
        ):
            self._boss_service.get_phase(
                raid_id=raid_id,
                phase_no=(
                    new_raid.current_phase
                ),
            )

        return RaidPhaseAdvanceResult(
            raid_id=raid.raid_id,

            previous_phase=(
                previous_phase
            ),

            current_phase=(
                new_raid.current_phase
            ),

            advanced=True,

            final_reached=(
                new_raid.current_phase
                == FINAL_REACHED_PHASE
            ),

            reason="phase_complete",

            defeated_count=5,

            missing_boss_nos=(),
        )

    def set_remaining_hp(
        self,
        raid_id: int,
        boss_no: int,
        remaining_hp: int,
    ) -> RaidBossProgressUpdateResult:
        """
        現在PhaseのBoss残HPを更新し、
        その直後にPhase終了判定も行う。

        今後、残HPを書き換える場合は
        原則こちらを使用する。
        """

        raid = (
            self._raid_service
            .get_by_id(
                raid_id
            )
        )

        if raid is None:
            raise ValueError(
                (
                    "Raidが存在しません: "
                    f"raid_id={raid_id}"
                )
            )

        if raid.final_reached:
            raise ValueError(
                (
                    "Phase 3まで攻略済みです。"
                    "最終フェーズは"
                    "このBotの最適化対象外です。"
                )
            )

        boss = (
            self._boss_service
            .set_remaining_hp(
                raid_id=raid_id,
                boss_no=boss_no,
                phase_no=(
                    raid.current_phase
                ),
                remaining_hp=(
                    remaining_hp
                ),
            )
        )

        transition = (
            self.evaluate_and_advance(
                raid_id
            )
        )

        return (
            RaidBossProgressUpdateResult(
                boss=boss,
                transition=transition,
            )
        )