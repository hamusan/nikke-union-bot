from __future__ import annotations

import hashlib
import secrets

from sqlalchemy import (
    delete,
    select,
)

from bot.core.database import session_scope
from bot.models import (
    Boss,
    BossPhase,
    Raid,
)
from bot.models.raid_attack import (
    RaidAttack,
)
from bot.models.raid_boss_progress import (
    RaidBossProgress,
)
from bot.services.raid_attack_coordinator_service import (
    RaidAttackCoordinatorService,
)


RAID_ID = 1
PLAYER_ID = 1
TEAM_ID = 1

TEST_DAMAGE = 12_345


def create_test_source() -> tuple[
    int,
    str,
]:
    source_message_id = (
        8_000_000_000_000_000_000
        + secrets.randbelow(
            100_000_000
        )
    )

    image_sha256 = hashlib.sha256(
        (
            "raid-phase-transition-"
            f"{source_message_id}"
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    return (
        source_message_id,
        image_sha256,
    )


def prepare_test():
    """
    現在DB状態を保存してから、
    現Phaseを

    Boss #1 = TEST_DAMAGE HP
    Boss #2～#5 = 0 HP

    の状態へする。
    """

    with session_scope() as session:
        raid = session.get(
            Raid,
            RAID_ID,
        )

        if raid is None:
            raise RuntimeError(
                "Raid not found"
            )

        original_phase = (
            raid.current_phase
        )

        if original_phase not in (
            1,
            2,
            3,
        ):
            raise RuntimeError(
                (
                    "現在Final Phaseのため"
                    "このテストは実行できません"
                )
            )

        bosses = list(
            session.scalars(
                select(Boss)
                .where(
                    Boss.raid_id
                    == RAID_ID
                )
                .order_by(
                    Boss.boss_no
                )
            ).all()
        )

        if {
            boss.boss_no
            for boss in bosses
        } != {
            1,
            2,
            3,
            4,
            5,
        }:
            raise RuntimeError(
                (
                    "Boss #1～#5が"
                    "すべて設定されていません"
                )
            )

        boss_ids = [
            boss.id
            for boss in bosses
        ]

        all_phases = list(
            session.scalars(
                select(BossPhase)
                .where(
                    BossPhase.boss_id.in_(
                        boss_ids
                    )
                )
            ).all()
        )

        all_phase_ids = {
            phase.id
            for phase in all_phases
        }

        # -----------------------------
        # 元Progressを全部保存
        # -----------------------------

        original_progress: dict[
            int,
            int,
        ] = {}

        if all_phase_ids:
            progress_rows = list(
                session.scalars(
                    select(
                        RaidBossProgress
                    )
                    .where(
                        RaidBossProgress
                        .boss_phase_id
                        .in_(
                            all_phase_ids
                        )
                    )
                ).all()
            )

            original_progress = {
                row.boss_phase_id:
                    row.remaining_hp
                for row in progress_rows
            }

        # -----------------------------
        # 現PhaseのBossPhase
        # -----------------------------

        current_phase_by_boss_id = {
            phase.boss_id: phase
            for phase in all_phases
            if (
                phase.phase_no
                == original_phase
            )
        }

        if len(
            current_phase_by_boss_id
        ) != 5:
            missing = [
                boss.boss_no
                for boss in bosses
                if boss.id
                not in (
                    current_phase_by_boss_id
                )
            ]

            raise RuntimeError(
                (
                    "現在PhaseのBossPhaseが"
                    "5体分設定されていません: "
                    f"missing={missing}"
                )
            )

        target_boss = next(
            boss
            for boss in bosses
            if boss.boss_no == 1
        )

        target_phase = (
            current_phase_by_boss_id[
                target_boss.id
            ]
        )

        if (
            target_phase.max_hp
            < TEST_DAMAGE
        ):
            raise RuntimeError(
                (
                    "Boss #1 max_hp が"
                    "TEST_DAMAGEより小さいです"
                )
            )

        # -----------------------------
        # Boss #1だけ少量HP
        # その他は撃破済みにする
        # -----------------------------

        for boss in bosses:
            phase = (
                current_phase_by_boss_id[
                    boss.id
                ]
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
                progress = (
                    RaidBossProgress(
                        boss_phase_id=(
                            phase.id
                        ),
                        remaining_hp=(
                            phase.max_hp
                        ),
                    )
                )

                session.add(
                    progress
                )

                session.flush()

            if boss.boss_no == 1:
                progress.remaining_hp = (
                    TEST_DAMAGE
                )
            else:
                progress.remaining_hp = 0

        return (
            original_phase,
            original_progress,
            all_phase_ids,
            target_boss.id,
        )


def cleanup(
    *,
    original_phase: int,
    original_progress: dict[
        int,
        int,
    ],
    all_phase_ids: set[int],
    source_message_id: int,
    image_sha256: str,
) -> None:
    """
    テストで変更したDBを元へ戻す。
    """

    with session_scope() as session:
        # -----------------------------
        # Test RaidAttack削除
        # -----------------------------

        session.execute(
            delete(RaidAttack)
            .where(
                (
                    RaidAttack
                    .source_message_id
                    == source_message_id
                )
                | (
                    RaidAttack
                    .image_sha256
                    == image_sha256
                )
            )
        )

        # -----------------------------
        # current_phase復元
        # -----------------------------

        raid = session.get(
            Raid,
            RAID_ID,
        )

        if raid is not None:
            raid.current_phase = (
                original_phase
            )

        # -----------------------------
        # Progress復元
        # -----------------------------

        current_progress_rows = list(
            session.scalars(
                select(
                    RaidBossProgress
                )
                .where(
                    RaidBossProgress
                    .boss_phase_id
                    .in_(
                        all_phase_ids
                    )
                )
            ).all()
        )

        for progress in (
            current_progress_rows
        ):
            if (
                progress.boss_phase_id
                in original_progress
            ):
                progress.remaining_hp = (
                    original_progress[
                        progress.boss_phase_id
                    ]
                )
            else:
                # テスト中に作られたProgress
                # は削除する。
                session.delete(
                    progress
                )


def main() -> None:
    (
        source_message_id,
        image_sha256,
    ) = create_test_source()

    original_phase = None
    original_progress = None
    all_phase_ids = None

    try:
        (
            original_phase,
            original_progress,
            all_phase_ids,
            target_boss_id,
        ) = prepare_test()

        print(
            "=== Raid Phase Transition Test ==="
        )

        print(
            "original phase =",
            original_phase,
        )

        print(
            "Boss #1 HP =",
            TEST_DAMAGE,
        )

        print(
            "Boss #2-#5 HP = 0"
        )

        service = (
            RaidAttackCoordinatorService()
        )

        result = service.record_attack(
            raid_id=RAID_ID,
            boss_id=target_boss_id,
            player_id=PLAYER_ID,
            team_id=TEAM_ID,
            damage=TEST_DAMAGE,
            source_message_id=(
                source_message_id
            ),
            image_sha256=(
                image_sha256
            ),
        )

        # -----------------------------
        # Attack
        # -----------------------------

        assert (
            result.attack.created
            is True
        )

        assert (
            result.attack.remaining_hp
            == 0
        )

        print(
            "[OK] final Boss defeated"
        )

        # -----------------------------
        # Phase transition
        # -----------------------------

        assert (
            result.transition.advanced
            is True
        )

        expected_phase = (
            original_phase + 1
        )

        assert (
            result.transition
            .previous_phase
            == original_phase
        )

        assert (
            result.transition
            .current_phase
            == expected_phase
        )

        print(
            "[OK] phase advanced:",
            original_phase,
            "->",
            expected_phase,
        )

        # -----------------------------
        # DB確認
        # -----------------------------

        with session_scope() as session:
            raid = session.get(
                Raid,
                RAID_ID,
            )

            assert raid is not None

            assert (
                raid.current_phase
                == expected_phase
            )

        print(
            "[OK] current_phase persisted"
        )

        if expected_phase == 4:
            assert (
                result.transition
                .final_reached
                is True
            )

            print(
                "[OK] final phase reached"
            )
        else:
            assert (
                result.transition
                .final_reached
                is False
            )

        print()
        print(
            "Raid Phase Transition TEST OK"
        )

    finally:
        if (
            original_phase is not None
            and original_progress
            is not None
            and all_phase_ids
            is not None
        ):
            cleanup(
                original_phase=(
                    original_phase
                ),
                original_progress=(
                    original_progress
                ),
                all_phase_ids=(
                    all_phase_ids
                ),
                source_message_id=(
                    source_message_id
                ),
                image_sha256=(
                    image_sha256
                ),
            )

            print()
            print(
                "[CLEANUP] Raid state restored"
            )


if __name__ == "__main__":
    main()