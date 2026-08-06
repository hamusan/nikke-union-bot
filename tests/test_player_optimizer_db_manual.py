from sqlalchemy import select

from bot.core.database import session_scope
from bot.models import Raid
from bot.services import (
    OptimizationCandidateService,
    PlayerOptimizationSolver,
)


def main() -> None:
    print()
    print(
        "DB Player Optimization Test"
    )
    print("=" * 60)

    # Active RaidをDBから自動取得する。
    with session_scope() as session:
        raid = session.scalar(
            select(Raid)
            .where(
                Raid.active.is_(True)
            )
            .order_by(
                Raid.id.desc()
            )
        )

        if raid is None:
            print(
                "Active Raidがありません。"
            )
            return

        raid_id = raid.id

        print(
            f"Active Raid ID: {raid_id}"
        )

    candidate_service = (
        OptimizationCandidateService()
    )

    candidates = (
        candidate_service.build_for_raid(
            raid_id=raid_id
        )
    )

    print(
        f"Optimization Candidates: "
        f"{len(candidates)}"
    )

    if not candidates:
        print(
            "最適化候補がありません。"
        )
        return

    player_ids = sorted(
        {
            candidate.player_id
            for candidate in candidates
        }
    )

    solver = (
        PlayerOptimizationSolver()
    )

    for player_id in player_ids:
        print()
        print(
            f"Player ID: {player_id}"
        )
        print("-" * 60)

        result = solver.solve(
            player_id=player_id,
            candidates=candidates,
            max_attacks=3,
        )

        for candidate in (
            result.selected_candidates
        ):
            print(
                f"Team #{candidate.team_no}"
                f" | "
                f"Boss={candidate.boss_id}"
                f" | "
                f"Phase={candidate.phase_no}"
                f" | "
                f"Damage={candidate.damage:,}"
                f" | "
                f"Characters="
                f"{candidate.character_ids}"
            )

        print(
            f"Total: "
            f"{result.total_damage:,}"
        )


if __name__ == "__main__":
    main()