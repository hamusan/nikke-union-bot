from __future__ import annotations

from sqlalchemy import (
    delete,
    select,
)

from bot.core.database import session_scope
from bot.models.boss import Boss
from bot.models.boss_phase import BossPhase
from bot.models.raid import Raid
from bot.models.raid_boss_progress import (
    RaidBossProgress,
)
from bot.services.raid_rebuild_service import (
    RaidRebuildService,
)
from bot.services.raid_service import RaidService


def main() -> None:
    raid = (
        RaidService()
        .get_active_raid()
    )

    raid_id = raid.id

    service = (
        RaidRebuildService()
    )

    # --------------------------------
    # 1. 現在状態を保存
    # --------------------------------

    original_phase: int

    original_progress: dict[
        int,
        int,
    ] = {}

    existing_progress_ids: set[
        int
    ] = set()

    with session_scope() as session:
        db_raid = session.get(
            Raid,
            raid_id,
        )

        if db_raid is None:
            raise RuntimeError(
                "Raid not found."
            )

        original_phase = (
            db_raid.current_phase
        )

        phases = list(
            session.scalars(
                select(
                    BossPhase
                )
                .join(
                    Boss,
                    Boss.id
                    == BossPhase.boss_id,
                )
                .where(
                    Boss.raid_id
                    == raid_id
                )
            ).all()
        )

        phase_ids = {
            phase.id
            for phase in phases
        }

        if phase_ids:
            progresses = list(
                session.scalars(
                    select(
                        RaidBossProgress
                    )
                    .where(
                        RaidBossProgress
                        .boss_phase_id
                        .in_(
                            phase_ids
                        )
                    )
                ).all()
            )

            for progress in progresses:
                original_progress[
                    progress.boss_phase_id
                ] = (
                    progress.remaining_hp
                )

                existing_progress_ids.add(
                    progress.boss_phase_id
                )

    print(
        "Original Phase =",
        original_phase,
    )

    print(
        "Original Progress rows =",
        len(
            original_progress
        ),
    )

    # --------------------------------
    # 2. Preview
    # --------------------------------

    preview = service.preview(
        raid_id
    )

    print()
    print(
        "Preview Phase =",
        preview.current_phase,
    )

    print(
        "Preview Applied attacks =",
        preview.applied_attack_count,
    )

    print(
        "Preview Cancelled attacks =",
        preview.cancelled_attack_count,
    )

    print(
        "Preview Blocked attacks =",
        preview.blocked_attack_count,
    )

    try:
        # --------------------------------
        # 3. 実際にrebuild
        # --------------------------------

        rebuilt = service.rebuild(
            raid_id
        )

        print()
        print(
            "Rebuilt Phase =",
            rebuilt.current_phase,
        )

        assert (
            rebuilt.current_phase
            == preview.current_phase
        )

        assert (
            rebuilt.applied_attack_count
            == preview.applied_attack_count
        )

        assert (
            rebuilt.cancelled_attack_count
            == preview.cancelled_attack_count
        )

        assert (
            rebuilt.blocked_attack_ids
            == preview.blocked_attack_ids
        )

        # --------------------------------
        # 4. DB確認
        # --------------------------------

        with session_scope() as session:
            db_raid = session.get(
                Raid,
                raid_id,
            )

            if db_raid is None:
                raise RuntimeError(
                    "Raid disappeared."
                )

            assert (
                db_raid.current_phase
                == rebuilt.current_phase
            )

            for boss_state in (
                rebuilt.bosses
            ):
                phase = session.scalar(
                    select(
                        BossPhase
                    )
                    .where(
                        BossPhase.boss_id
                        == boss_state.boss_id
                    )
                    .where(
                        BossPhase.phase_no
                        == boss_state.phase_no
                    )
                )

                if phase is None:
                    raise AssertionError(
                        (
                            "BossPhase missing: "
                            f"boss_id="
                            f"{boss_state.boss_id}, "
                            f"phase="
                            f"{boss_state.phase_no}"
                        )
                    )

                progress = session.scalar(
                    select(
                        RaidBossProgress
                    )
                    .where(
                        RaidBossProgress
                        .boss_phase_id
                        == phase.id
                    )
                )

                if progress is None:
                    raise AssertionError(
                        (
                            "Progress missing: "
                            f"phase_id={phase.id}"
                        )
                    )

                assert (
                    progress.remaining_hp
                    == boss_state.remaining_hp
                )

        print(
            "[OK] DB Phase matches rebuild"
        )

        print(
            "[OK] DB Boss HP matches rebuild"
        )

        print(
            "Raid Rebuild TEST OK"
        )

    finally:
        # --------------------------------
        # 5. 元の状態へ完全復元
        # --------------------------------

        with session_scope() as session:
            db_raid = session.get(
                Raid,
                raid_id,
            )

            if db_raid is not None:
                db_raid.current_phase = (
                    original_phase
                )

            phases = list(
                session.scalars(
                    select(
                        BossPhase
                    )
                    .join(
                        Boss,
                        Boss.id
                        == BossPhase.boss_id,
                    )
                    .where(
                        Boss.raid_id
                        == raid_id
                    )
                ).all()
            )

            phase_ids = {
                phase.id
                for phase in phases
            }

            # 元々存在したProgressを復元
            for (
                boss_phase_id,
                remaining_hp,
            ) in original_progress.items():
                progress = session.scalar(
                    select(
                        RaidBossProgress
                    )
                    .where(
                        RaidBossProgress
                        .boss_phase_id
                        == boss_phase_id
                    )
                )

                if progress is not None:
                    progress.remaining_hp = (
                        remaining_hp
                    )

            # rebuild()によって新規作成された
            # Progressだけ削除
            created_phase_ids = (
                phase_ids
                - existing_progress_ids
            )

            if created_phase_ids:
                session.execute(
                    delete(
                        RaidBossProgress
                    )
                    .where(
                        RaidBossProgress
                        .boss_phase_id
                        .in_(
                            created_phase_ids
                        )
                    )
                )

        print(
            "[CLEANUP] "
            "Raid Phase restored to",
            original_phase,
        )

        print(
            "[CLEANUP] "
            "Boss HP restored"
        )


if __name__ == "__main__":
    main()