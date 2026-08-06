from bot.services import (
    OptimizationCandidate,
    UnionOptimizationSolver,
)


def make_candidate(
    record_id: int,
    player_id: int,
    team_id: int,
    team_no: int,
    boss_id: int,
    boss_phase_id: int,
    damage: int,
    characters: tuple[int, ...],
) -> OptimizationCandidate:
    return OptimizationCandidate(
        damage_record_id=record_id,

        player_id=player_id,

        team_id=team_id,
        team_no=team_no,

        boss_id=boss_id,
        boss_phase_id=boss_phase_id,
        phase_no=1,

        damage=damage,

        character_ids=characters,
    )


def main() -> None:
    print()
    print(
        "Union Optimization Solver Test"
    )
    print("=" * 70)

    candidates = [
        # --------------------------------
        # Player 1
        # --------------------------------

        make_candidate(
            record_id=1,
            player_id=1,
            team_id=1,
            team_no=1,
            boss_id=1,
            boss_phase_id=1,
            damage=100,
            characters=(
                1,
                2,
                3,
                4,
                5,
            ),
        ),

        make_candidate(
            record_id=2,
            player_id=1,
            team_id=2,
            team_no=2,
            boss_id=2,
            boss_phase_id=2,
            damage=90,
            characters=(
                1,
                6,
                7,
                8,
                9,
            ),
        ),

        # ↑ Character #1が重複しているので、
        # Player 1はTeam #1と#2を
        # 同時には使えない。

        # --------------------------------
        # Player 2
        # --------------------------------

        make_candidate(
            record_id=3,
            player_id=2,
            team_id=3,
            team_no=1,
            boss_id=2,
            boss_phase_id=2,
            damage=100,
            characters=(
                1,
                2,
                3,
                4,
                5,
            ),
        ),

        # Player 1と全く同じCharacter IDだが、
        # Playerが別なので使用可能。
    ]

    boss_hp_by_phase_id = {
        1: 100,
        2: 100,
    }

    solver = (
        UnionOptimizationSolver()
    )

    result = solver.solve(
        candidates=candidates,
        boss_hp_by_phase_id=(
            boss_hp_by_phase_id
        ),
        max_attacks_per_player=3,
    )

    print(
        f"Attack Count: "
        f"{result.attack_count}"
    )

    print(
        f"Nominal Damage: "
        f"{result.total_nominal_damage}"
    )

    print(
        f"Effective Damage: "
        f"{result.total_effective_damage}"
    )

    print()

    print("Selected")
    print("-" * 70)

    for candidate in (
        result.selected_candidates
    ):
        print(
            f"Player={candidate.player_id}"
            f" | "
            f"Team=#{candidate.team_no}"
            f" | "
            f"Boss={candidate.boss_id}"
            f" | "
            f"Damage={candidate.damage}"
            f" | "
            f"Chars={candidate.character_ids}"
        )

    print()

    print("Boss Plans")
    print("-" * 70)

    for plan in result.boss_plans:
        print(
            f"Boss={plan.boss_id}"
            f" | "
            f"Phase={plan.phase_no}"
            f" | "
            f"HP={plan.max_hp}"
            f" | "
            f"Nominal={plan.nominal_damage}"
            f" | "
            f"Effective={plan.effective_damage}"
            f" | "
            f"Overkill={plan.overkill_damage}"
        )


if __name__ == "__main__":
    main()