from __future__ import annotations

from bot.services.optimization.candidate import (
    OptimizationCandidate,
)
from bot.services.optimization.union_solver import (
    UnionOptimizationSolver,
)


def make_candidate(
    record_id: int,
    player_id: int,
    team_id: int,
    team_no: int,
    boss_id: int,
    phase_id: int,
    phase_no: int,
    damage: int,
    characters: tuple[int, int, int, int, int],
) -> OptimizationCandidate:
    """テスト用Candidateを作る。"""

    return OptimizationCandidate(
        damage_record_id=record_id,

        player_id=player_id,

        team_id=team_id,
        team_no=team_no,

        boss_id=boss_id,
        boss_phase_id=phase_id,
        phase_no=phase_no,

        damage=damage,

        character_ids=characters,
    )


def selected_ids(
    result,
) -> set[int]:
    """選択されたDamageRecord IDを取得する。"""

    return {
        candidate.damage_record_id
        for candidate
        in result.selected_candidates
    }


def scenario_max_three_attacks() -> None:
    """
    1 Playerにつき最大3凸。

    4候補あっても、
    Damage上位3つだけが選択される。
    """

    solver = UnionOptimizationSolver()

    candidates = [
        make_candidate(
            1,
            1,
            101,
            1,
            1,
            1001,
            3,
            400,
            (1, 2, 3, 4, 5),
        ),
        make_candidate(
            2,
            1,
            102,
            2,
            1,
            1001,
            3,
            300,
            (6, 7, 8, 9, 10),
        ),
        make_candidate(
            3,
            1,
            103,
            3,
            1,
            1001,
            3,
            200,
            (11, 12, 13, 14, 15),
        ),
        make_candidate(
            4,
            1,
            104,
            4,
            1,
            1001,
            3,
            100,
            (16, 17, 18, 19, 20),
        ),
    ]

    result = solver.solve(
        candidates=candidates,
        boss_hp_by_phase_id={
            1001: 1_000,
        },
        max_attacks_per_player=3,
    )

    assert selected_ids(result) == {
        1,
        2,
        3,
    }

    assert result.attack_count == 3

    assert (
        result.total_effective_damage
        == 900
    )

    print(
        "[OK] Scenario 1:"
        " max 3 attacks"
    )


def scenario_character_overlap() -> None:
    """
    同じPlayerの別Teamで
    Characterが1人でも重複する場合、
    両方同時には選べない。
    """

    solver = UnionOptimizationSolver()

    candidates = [
        # Team #1
        make_candidate(
            11,
            1,
            201,
            1,
            1,
            2001,
            3,
            400,
            (1, 2, 3, 4, 5),
        ),

        # Team #2
        # Character 5 がTeam #1と重複
        make_candidate(
            12,
            1,
            202,
            2,
            1,
            2001,
            3,
            350,
            (5, 6, 7, 8, 9),
        ),

        # Team #3
        # 完全に別Character
        make_candidate(
            13,
            1,
            203,
            3,
            1,
            2001,
            3,
            300,
            (10, 11, 12, 13, 14),
        ),
    ]

    result = solver.solve(
        candidates=candidates,
        boss_hp_by_phase_id={
            2001: 1_000,
        },
        max_attacks_per_player=3,
    )

    # Team1 + Team3 = 700
    #
    # Team2 + Team3 = 650
    #
    # Team1 + Team2 はCharacter重複で不可。
    assert selected_ids(result) == {
        11,
        13,
    }

    assert (
        result.total_effective_damage
        == 700
    )

    print(
        "[OK] Scenario 2:"
        " character overlap"
    )


def scenario_same_team_cannot_repeat() -> None:
    """
    同一Playerが同じTeamを
    複数攻撃へ使えないことを確認する。

    Characterは意図的に別にして、
    Team制約そのものをテストする。
    """

    solver = UnionOptimizationSolver()

    candidates = [
        # Team ID 301
        make_candidate(
            21,
            1,
            301,
            1,
            1,
            3001,
            3,
            400,
            (1, 2, 3, 4, 5),
        ),

        # 同じTeam ID 301
        # Characterは別にする
        make_candidate(
            22,
            1,
            301,
            1,
            2,
            3002,
            3,
            350,
            (6, 7, 8, 9, 10),
        ),

        # Team ID 302
        make_candidate(
            23,
            1,
            302,
            2,
            2,
            3002,
            3,
            300,
            (11, 12, 13, 14, 15),
        ),
    ]

    result = solver.solve(
        candidates=candidates,
        boss_hp_by_phase_id={
            3001: 1_000,
            3002: 1_000,
        },
        max_attacks_per_player=3,
    )

    # 21 + 23 = 700 が最適。
    #
    # 21 + 22 + 23 は
    # 同じTeamを2回使うため不可。
    assert selected_ids(result) == {
        21,
        23,
    }

    assert (
        result.total_effective_damage
        == 700
    )

    print(
        "[OK] Scenario 3:"
        " team uniqueness"
    )


def scenario_characters_are_per_player() -> None:
    """
    Character使用制限はPlayer単位。

    Playerが違えば同じCharacter編成を
    使ってもよい。
    """

    solver = UnionOptimizationSolver()

    candidates = [
        make_candidate(
            31,
            1,
            401,
            1,
            1,
            4001,
            3,
            400,
            (1, 2, 3, 4, 5),
        ),
        make_candidate(
            32,
            2,
            402,
            1,
            2,
            4002,
            3,
            300,
            (1, 2, 3, 4, 5),
        ),
    ]

    result = solver.solve(
        candidates=candidates,
        boss_hp_by_phase_id={
            4001: 1_000,
            4002: 1_000,
        },
        max_attacks_per_player=3,
    )

    assert selected_ids(result) == {
        31,
        32,
    }

    assert result.attack_count == 2

    assert (
        result.total_effective_damage
        == 700
    )

    print(
        "[OK] Scenario 4:"
        " same characters across players"
    )


def scenario_boss_hp_and_overkill() -> None:
    """
    Boss HPを超えたDamageは
    有効Damageとして加算されない。
    """

    solver = UnionOptimizationSolver()

    candidates = [
        # Boss 1:
        # 700 Damage
        # HP 500
        make_candidate(
            41,
            1,
            501,
            1,
            1,
            5001,
            3,
            700,
            (1, 2, 3, 4, 5),
        ),

        # Boss 2:
        # 300 Damage
        # HP 400
        make_candidate(
            42,
            2,
            502,
            1,
            2,
            5002,
            3,
            300,
            (1, 2, 3, 4, 5),
        ),
    ]

    result = solver.solve(
        candidates=candidates,
        boss_hp_by_phase_id={
            5001: 500,
            5002: 400,
        },
        max_attacks_per_player=3,
    )

    assert selected_ids(result) == {
        41,
        42,
    }

    # nominal
    # 700 + 300
    assert (
        result.total_nominal_damage
        == 1_000
    )

    # effective
    # min(700, 500)
    # +
    # min(300, 400)
    #
    # = 800
    assert (
        result.total_effective_damage
        == 800
    )

    boss_plan_by_phase = {
        plan.boss_phase_id: plan
        for plan in result.boss_plans
    }

    boss1 = boss_plan_by_phase[
        5001
    ]

    boss2 = boss_plan_by_phase[
        5002
    ]

    assert (
        boss1.max_hp
        == 500
    )

    assert (
        boss1.nominal_damage
        == 700
    )

    assert (
        boss1.effective_damage
        == 500
    )

    assert (
        boss1.overkill_damage
        == 200
    )

    assert (
        boss2.max_hp
        == 400
    )

    assert (
        boss2.nominal_damage
        == 300
    )

    assert (
        boss2.effective_damage
        == 300
    )

    assert (
        boss2.overkill_damage
        == 0
    )

    print(
        "[OK] Scenario 5:"
        " Boss HP / Overkill"
    )


def scenario_minimum_attack_count() -> None:
    """
    同じ最大有効Damageを達成できるなら、
    少ない凸数を選ぶ。

    500を1凸で出せるCandidateと、
    250 + 250 の2凸がある。
    """

    solver = UnionOptimizationSolver()

    candidates = [
        make_candidate(
            51,
            1,
            601,
            1,
            1,
            6001,
            3,
            500,
            (1, 2, 3, 4, 5),
        ),
        make_candidate(
            52,
            2,
            602,
            1,
            1,
            6001,
            3,
            250,
            (1, 2, 3, 4, 5),
        ),
        make_candidate(
            53,
            3,
            603,
            1,
            1,
            6001,
            3,
            250,
            (1, 2, 3, 4, 5),
        ),
    ]

    result = solver.solve(
        candidates=candidates,
        boss_hp_by_phase_id={
            6001: 500,
        },
        max_attacks_per_player=3,
    )

    # 51単独でも500。
    #
    # 52 + 53でも500。
    #
    # 有効Damageが同じなら
    # 1凸の51を選ぶ。
    assert selected_ids(result) == {
        51,
    }

    assert result.attack_count == 1

    assert (
        result.total_effective_damage
        == 500
    )

    print(
        "[OK] Scenario 6:"
        " minimum attack count"
    )


def scenario_missing_boss_hp_rejected() -> None:
    """
    Candidateが参照するBossPhaseのHPが
    入力されていない場合は
    エラーになることを確認する。
    """

    solver = UnionOptimizationSolver()

    candidates = [
        make_candidate(
            61,
            1,
            701,
            1,
            1,
            7001,
            3,
            100,
            (1, 2, 3, 4, 5),
        ),
    ]

    try:
        solver.solve(
            candidates=candidates,

            # 7001が無い
            boss_hp_by_phase_id={},

            max_attacks_per_player=3,
        )

    except ValueError as exc:
        print(
            "[OK] Scenario 7:"
            " missing Boss HP rejected"
        )

        print(
            "     Error:",
            exc,
        )

        return

    raise AssertionError(
        (
            "Boss HPが無いにもかかわらず"
            "ValueErrorになりませんでした。"
        )
    )


def main() -> None:
    print(
        "========================================"
    )
    print(
        "Union Optimization Solver Scenarios"
    )
    print(
        "========================================"
    )
    print()

    scenario_max_three_attacks()
    scenario_character_overlap()
    scenario_same_team_cannot_repeat()
    scenario_characters_are_per_player()
    scenario_boss_hp_and_overkill()
    scenario_minimum_attack_count()
    scenario_missing_boss_hp_rejected()

    print()
    print(
        "========================================"
    )
    print(
        "ALL UNION SOLVER SCENARIOS OK"
    )
    print(
        "========================================"
    )


if __name__ == "__main__":
    main()