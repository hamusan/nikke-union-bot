from bot.services import (
    OptimizationCandidate,
    PlayerOptimizationSolver,
)


def make_candidate(
    record_id: int,
    team_id: int,
    team_no: int,
    damage: int,
    characters: tuple[int, ...],
) -> OptimizationCandidate:
    return OptimizationCandidate(
        damage_record_id=record_id,

        player_id=1,

        team_id=team_id,
        team_no=team_no,

        boss_id=1,
        boss_phase_id=1,
        phase_no=1,

        damage=damage,

        character_ids=characters,
    )


def main() -> None:
    print()
    print(
        "Player Optimization Solver Test"
    )
    print("=" * 60)

    candidates = [
        # Team #1
        # 100億
        make_candidate(
            record_id=1,
            team_id=1,
            team_no=1,
            damage=10_000_000_000,
            characters=(
                1,
                2,
                3,
                4,
                5,
            ),
        ),

        # Team #2
        # 120億
        #
        # Character #5 が
        # Team #1と重複。
        make_candidate(
            record_id=2,
            team_id=2,
            team_no=2,
            damage=12_000_000_000,
            characters=(
                5,
                6,
                7,
                8,
                9,
            ),
        ),

        # Team #3
        # 80億
        # 完全独立。
        make_candidate(
            record_id=3,
            team_id=3,
            team_no=3,
            damage=8_000_000_000,
            characters=(
                10,
                11,
                12,
                13,
                14,
            ),
        ),

        # Team #4
        # 70億
        # 完全独立。
        make_candidate(
            record_id=4,
            team_id=4,
            team_no=4,
            damage=7_000_000_000,
            characters=(
                15,
                16,
                17,
                18,
                19,
            ),
        ),
    ]

    solver = (
        PlayerOptimizationSolver()
    )

    result = solver.solve(
        player_id=1,
        candidates=candidates,
        max_attacks=3,
    )

    print(
        f"Player: {result.player_id}"
    )

    print(
        f"Selected: "
        f"{len(result.selected_candidates)}"
    )

    print()

    for candidate in (
        result.selected_candidates
    ):
        print(
            f"Team #{candidate.team_no}"
            f" | "
            f"Damage="
            f"{candidate.damage:,}"
            f" | "
            f"Characters="
            f"{candidate.character_ids}"
        )

    print()

    print(
        f"Total Damage: "
        f"{result.total_damage:,}"
    )


if __name__ == "__main__":
    main()