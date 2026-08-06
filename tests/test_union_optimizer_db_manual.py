from sqlalchemy import select

from bot.core.database import (
    session_scope,
)
from bot.models import (
    BossPhase,
    Raid,
)
from bot.services import (
    OptimizationCandidateService,
    UnionOptimizationSolver,
)


def main() -> None:
    print()
    print(
        "DB Union Optimization Test"
    )
    print("=" * 70)

    # --------------------------------
    # Active Raid
    # --------------------------------

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

    # --------------------------------
    # Candidate
    # --------------------------------

    candidate_service = (
        OptimizationCandidateService()
    )

    candidates = (
        candidate_service.build_for_raid(
            raid_id=raid_id
        )
    )

    print(
        f"Candidates: {len(candidates)}"
    )

    if not candidates:
        print(
            "最適化候補がありません。"
        )
        return

    # --------------------------------
    # Candidateで使用されている
    # BossPhaseの最大HP取得
    # --------------------------------

    phase_ids = {
        candidate.boss_phase_id
        for candidate in candidates
    }

    with session_scope() as session:
        phases = list(
            session.scalars(
                select(BossPhase)
                .where(
                    BossPhase.id.in_(
                        phase_ids
                    )
                )
            ).all()
        )

        boss_hp_by_phase_id = {
            phase.id: phase.max_hp
            for phase in phases
        }

    print()
    print("Boss HP")

    for (
        phase_id,
        hp,
    ) in sorted(
        boss_hp_by_phase_id.items()
    ):
        print(
            f"  Phase ID {phase_id}: "
            f"{hp:,}"
        )

    # --------------------------------
    # Optimization
    # --------------------------------

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

    print()
    print(
        f"Attack Count: "
        f"{result.attack_count}"
    )

    print(
        f"Nominal Damage: "
        f"{result.total_nominal_damage:,}"
    )

    print(
        f"Effective Damage: "
        f"{result.total_effective_damage:,}"
    )

    print()

    print("Selected Attacks")
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
            f"Phase={candidate.phase_no}"
            f" | "
            f"Damage={candidate.damage:,}"
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
            f"HP={plan.max_hp:,}"
            f" | "
            f"Damage={plan.nominal_damage:,}"
            f" | "
            f"Effective={plan.effective_damage:,}"
            f" | "
            f"Overkill={plan.overkill_damage:,}"
        )


if __name__ == "__main__":
    main()