from __future__ import annotations

from dataclasses import dataclass


PHASE_1 = 1
PHASE_2 = 2
PHASE_3 = 3

FINAL_REACHED_PHASE = 4

FIRST_PHASE = PHASE_1
LAST_OPTIMIZATION_PHASE = PHASE_3


@dataclass(
    frozen=True
)
class RaidProgressState:
    """
    Raid全体の進行状態。

    current_phase:
        1 = Phase 1攻略中
        2 = Phase 2攻略中
        3 = Phase 3攻略中
        4 = 最終フェーズ到達済み
    """

    raid_id: int
    raid_name: str

    current_phase: int

    @property
    def final_reached(
        self,
    ) -> bool:
        return (
            self.current_phase
            == FINAL_REACHED_PHASE
        )

    @property
    def optimization_available(
        self,
    ) -> bool:
        return (
            FIRST_PHASE
            <= self.current_phase
            <= LAST_OPTIMIZATION_PHASE
        )

    @property
    def phase_label(
        self,
    ) -> str:
        if self.final_reached:
            return (
                "最終フェーズ到達済み"
            )

        return (
            f"Phase {self.current_phase}"
        )


@dataclass(
    frozen=True
)
class PhaseTransitionDecision:
    """
    現在Phaseを次へ進めてよいかの判定結果。
    """

    should_advance: bool

    reason: str


def validate_phase(
    phase_no: int,
) -> None:
    """
    Raid進行値を検証する。

    1～3:
        最適化対象Phase

    4:
        最終フェーズ到達済み
    """

    if not (
        FIRST_PHASE
        <= phase_no
        <= FINAL_REACHED_PHASE
    ):
        raise ValueError(
            (
                "current_phaseは"
                "1～4である必要があります: "
                f"{phase_no}"
            )
        )


def next_phase(
    current_phase: int,
) -> int:
    """
    次のPhase状態を返す。

    1 -> 2
    2 -> 3
    3 -> 4
    4 -> 4
    """

    validate_phase(
        current_phase
    )

    if (
        current_phase
        >= FINAL_REACHED_PHASE
    ):
        return FINAL_REACHED_PHASE

    return current_phase + 1


def is_final_reached(
    phase_no: int,
) -> bool:
    validate_phase(
        phase_no
    )

    return (
        phase_no
        == FINAL_REACHED_PHASE
    )


def decide_phase_transition(
    current_phase: int,
    all_bosses_configured: bool,
    all_bosses_defeated: bool,
) -> PhaseTransitionDecision:
    """
    現在Phaseを次へ進めるべきか判定する。

    Bossデータが5体分揃っていない場合は、
    誤ってPhaseを進めない。
    """

    validate_phase(
        current_phase
    )

    if (
        current_phase
        == FINAL_REACHED_PHASE
    ):
        return PhaseTransitionDecision(
            should_advance=False,
            reason="final_reached",
        )

    if not all_bosses_configured:
        return PhaseTransitionDecision(
            should_advance=False,
            reason=(
                "boss_config_incomplete"
            ),
        )

    if not all_bosses_defeated:
        return PhaseTransitionDecision(
            should_advance=False,
            reason="bosses_remaining",
        )

    return PhaseTransitionDecision(
        should_advance=True,
        reason="phase_complete",
    )