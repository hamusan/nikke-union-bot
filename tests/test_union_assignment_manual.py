from sqlalchemy import select

from bot.core.database import session_scope
from bot.models import Raid
from bot.services import (
    UnionAssignmentService,
)


def main() -> None:
    print()
    print(
        "Union Assignment Test"
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
    # Assignment
    # --------------------------------

    service = (
        UnionAssignmentService()
    )

    plan = service.build_for_raid(
        raid_id=raid_id,
        max_attacks_per_player=3,
    )

    print(
        f"Attack Count: "
        f"{plan.attack_count}"
    )

    print(
        f"Total Damage: "
        f"{plan.total_nominal_damage:,}"
    )

    print(
        f"Effective Damage: "
        f"{plan.total_effective_damage:,}"
    )

    if not plan.assignments:
        print()
        print(
            "攻撃割り当てがありません。"
        )
        return

    print()

    # --------------------------------
    # Bossごとの割り当て
    # --------------------------------

    for boss in plan.boss_summaries:
        print("=" * 70)

        print(
            f"{boss.boss_name} "
            f"| Phase {boss.phase_no}"
        )

        print(
            f"HP: "
            f"{boss.max_hp:,}"
        )

        print(
            f"Assigned Damage: "
            f"{boss.assigned_damage:,}"
        )

        print(
            f"Effective Damage: "
            f"{boss.effective_damage:,}"
        )

        print(
            f"Overkill: "
            f"{boss.overkill_damage:,}"
        )

        print("-" * 70)

        for assignment in (
            boss.assignments
        ):
            print(
                f"Player: "
                f"{assignment.player_name}"
            )

            print(
                f"Team: "
                f"#{assignment.team_no}"
            )

            print(
                f"Damage: "
                f"{assignment.damage:,}"
            )

            print(
                "Characters:"
            )

            for character_name in (
                assignment.character_names
            ):
                print(
                    f"  - {character_name}"
                )

            print()


if __name__ == "__main__":
    main()