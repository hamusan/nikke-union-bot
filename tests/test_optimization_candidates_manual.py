from sqlalchemy import select

from bot.core.database import session_scope
from bot.models import Raid
from bot.services import (
    OptimizationCandidateService,
)


def main() -> None:
    print()
    print("Optimization Candidate Test")
    print("=" * 60)

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
            f"Raid ID: {raid_id}"
        )

    service = (
        OptimizationCandidateService()
    )

    candidates = (
        service.build_for_raid(
            raid_id
        )
    )

    print(
        f"Candidates: {len(candidates)}"
    )

    print()

    for candidate in candidates:
        print("-" * 60)

        print(
            f"DamageRecord : "
            f"{candidate.damage_record_id}"
        )

        print(
            f"Player       : "
            f"{candidate.player_id}"
        )

        print(
            f"Team         : "
            f"#{candidate.team_no} "
            f"(id={candidate.team_id})"
        )

        print(
            f"Boss         : "
            f"{candidate.boss_id}"
        )

        print(
            f"Phase        : "
            f"{candidate.phase_no}"
        )

        print(
            f"Damage       : "
            f"{candidate.damage:,}"
        )

        print(
            f"Characters   : "
            f"{candidate.character_ids}"
        )


if __name__ == "__main__":
    main()