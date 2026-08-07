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

    current_phase=4 は、
    最終フェーズの攻略中という意味ではなく、
    Phase 3まで攻略完了したことを表す。
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
            return "最終フェーズ到達済み"

        return (
            f"Phase {self.current_phase}"
        )


def validate_phase(
    phase_no: int,
) -> None:
    """
    Raid進行値を検証する。

    1～3:
        攻略対象Phase

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
    Raidを次のPhaseへ進めた場合の値を返す。

    1 -> 2
    2 -> 3
    3 -> 4（最終フェーズ到達）
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