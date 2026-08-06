from dataclasses import dataclass


@dataclass(frozen=True)
class OptimizationCandidate:
    """
    OR-Toolsへ渡す1つの攻撃候補。

    例:
        Player A
        Team #2
        Boss #1
        Phase 3
        Damage 20,000,000,000
    """

    damage_record_id: int

    player_id: int
    team_id: int
    team_no: int

    boss_id: int
    boss_phase_id: int
    phase_no: int

    damage: int

    character_ids: tuple[int, ...]