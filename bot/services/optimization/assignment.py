from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AttackAssignment:
    """1回の攻撃割り当て。"""

    damage_record_id: int

    player_id: int
    player_name: str

    team_id: int
    team_no: int

    character_names: tuple[
        str,
        ...
    ]

    boss_id: int
    boss_name: str

    boss_phase_id: int
    phase_no: int

    damage: int


@dataclass(frozen=True)
class BossAssignmentSummary:
    """
    Bossごとの最適化結果。

    max_hp:
        そのPhaseにおけるBoss本来の最大HP

    remaining_hp:
        最適化開始時点の現在残HP
    """

    boss_id: int
    boss_name: str

    boss_phase_id: int
    phase_no: int

    max_hp: int
    remaining_hp: int

    assignments: tuple[
        AttackAssignment,
        ...
    ]

    assigned_damage: int
    effective_damage: int
    overkill_damage: int

    @property
    def defeated(
        self,
    ) -> bool:
        return (
            self.remaining_hp <= 0
        )

    @property
    def damage_taken(
        self,
    ) -> int:
        return max(
            0,
            self.max_hp
            - self.remaining_hp,
        )


@dataclass(frozen=True)
class UnionAssignmentPlan:
    """Raid全体の最適化結果。"""

    raid_id: int

    assignments: tuple[
        AttackAssignment,
        ...
    ]

    boss_summaries: tuple[
        BossAssignmentSummary,
        ...
    ]

    attack_count: int

    total_nominal_damage: int
    total_effective_damage: int