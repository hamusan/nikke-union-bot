from dataclasses import dataclass


@dataclass(frozen=True)
class AttackAssignment:
    """
    1つの攻撃割り当て。

    「誰が・どの編成で・どのBossを殴るか」
    を人間が読める形で保持する。
    """

    damage_record_id: int

    player_id: int
    player_name: str

    team_id: int
    team_no: int

    character_names: tuple[str, ...]

    boss_id: int
    boss_name: str

    boss_phase_id: int
    phase_no: int

    damage: int


@dataclass(frozen=True)
class BossAssignmentSummary:
    """Bossごとの割り当て結果。"""

    boss_id: int
    boss_name: str

    boss_phase_id: int
    phase_no: int

    max_hp: int

    assignments: tuple[
        AttackAssignment,
        ...
    ]

    assigned_damage: int
    effective_damage: int
    overkill_damage: int


@dataclass(frozen=True)
class UnionAssignmentPlan:
    """ユニオン全体の攻撃割り当て結果。"""

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