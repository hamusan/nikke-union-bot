from __future__ import annotations

from sqlalchemy import delete, select

from bot.core.database import (
    session_scope,
)
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
from bot.services.raid_attack_progress_service import (
    RaidAttackProgressService,
)


RAID_ID = 1
BOSS_ID = 1
PLAYER_ID = 1
TEAM_ID = 1

DAMAGE = 12_345

SOURCE_MESSAGE_ID = 9_990_100_001

IMAGE_SHA256 = "c" * 64


def get_current_state() -> tuple[
    int,
    int,
    int,
]:
    """
    current_phase,
    boss_phase_id,
    remaining_hp
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

        if raid.current_phase > 3:
            raise RuntimeError(
                (
                    "Raid is already "
                    "in final phase"
                )
            )

        boss = session.get(
            Boss,
            BOSS_ID,
        )

        if boss is None:
            raise RuntimeError(
                "Boss not found"
            )

        phase = session.scalar(
            select(BossPhase)
            .where(
                BossPhase.boss_id
                == BOSS_ID
            )
            .where(
                BossPhase.phase_no
                == raid.current_phase
            )
        )

        if phase is None:
            raise RuntimeError(
                (
                    "Current BossPhase "
                    "is not configured"
                )
            )

        progress = session.scalar(
            select(RaidBossProgress)
            .where(
                RaidBossProgress
                .boss_phase_id
                == phase.id
            )
        )

        if progress is None:
            progress = RaidBossProgress(
                boss_phase_id=phase.id,
                remaining_hp=phase.max_hp,
            )

            session.add(
                progress
            )

            session.flush()

        return (
            raid.current_phase,
            phase.id,
            progress.remaining_hp,
        )


def get_remaining_hp(
    boss_phase_id: int,
) -> int:
    with session_scope() as session:
        progress = session.scalar(
            select(RaidBossProgress)
            .where(
                RaidBossProgress
                .boss_phase_id
                == boss_phase_id
            )
        )

        if progress is None:
            raise RuntimeError(
                "Progress not found"
            )

        return progress.remaining_hp


def cleanup(
    *,
    boss_phase_id: int,
    original_remaining_hp: int,
) -> None:
    with session_scope() as session:
        session.execute(
            delete(RaidAttack)
            .where(
                RaidAttack.source_message_id
                == SOURCE_MESSAGE_ID
            )
        )

        progress = session.scalar(
            select(RaidBossProgress)
            .where(
                RaidBossProgress
                .boss_phase_id
                == boss_phase_id
            )
        )

        if progress is not None:
            progress.remaining_hp = (
                original_remaining_hp
            )


def main() -> None:
    (
        current_phase,
        boss_phase_id,
        original_remaining_hp,
    ) = get_current_state()

    print(
        "=== RaidAttack Progress Test ==="
    )

    print(
        "phase =",
        current_phase,
    )

    print(
        "original HP =",
        original_remaining_hp,
    )

    if original_remaining_hp <= DAMAGE:
        raise RuntimeError(
            (
                "テスト用Damageより"
                "現在HPが少ないため"
                "テストを中止します"
            )
        )

    service = (
        RaidAttackProgressService()
    )

    try:
        # --------------------------------
        # 1回目
        # --------------------------------

        first = service.record_and_apply(
            raid_id=RAID_ID,
            boss_id=BOSS_ID,
            player_id=PLAYER_ID,
            team_id=TEAM_ID,
            damage=DAMAGE,
            source_message_id=(
                SOURCE_MESSAGE_ID
            ),
            image_sha256=(
                IMAGE_SHA256
            ),
        )

        assert first.created is True

        expected_hp = (
            original_remaining_hp
            - DAMAGE
        )

        assert (
            first.previous_remaining_hp
            == original_remaining_hp
        )

        assert (
            first.remaining_hp
            == expected_hp
        )

        assert (
            first.applied_damage
            == DAMAGE
        )

        print(
            "[OK] RaidAttack created"
        )

        print(
            "[OK] HP decreased:",
            original_remaining_hp,
            "->",
            expected_hp,
        )

        # --------------------------------
        # DBでも確認
        # --------------------------------

        hp_after_first = (
            get_remaining_hp(
                boss_phase_id
            )
        )

        assert (
            hp_after_first
            == expected_hp
        )

        print(
            "[OK] HP persisted"
        )

        # --------------------------------
        # 同じMessageを再処理
        # --------------------------------

        second = (
            service.record_and_apply(
                raid_id=RAID_ID,
                boss_id=BOSS_ID,
                player_id=PLAYER_ID,
                team_id=TEAM_ID,
                damage=DAMAGE,
                source_message_id=(
                    SOURCE_MESSAGE_ID
                ),
                image_sha256=(
                    IMAGE_SHA256
                ),
            )
        )

        assert second.created is False

        hp_after_duplicate = (
            get_remaining_hp(
                boss_phase_id
            )
        )

        assert (
            hp_after_duplicate
            == expected_hp
        )

        print(
            "[OK] duplicate prevented"
        )

        print(
            "[OK] HP was not decreased twice"
        )

        print()
        print(
            "RaidAttack Progress TEST OK"
        )

    finally:
        cleanup(
            boss_phase_id=(
                boss_phase_id
            ),
            original_remaining_hp=(
                original_remaining_hp
            ),
        )

        print()
        print(
            "[CLEANUP] test attack removed"
        )

        print(
            "[CLEANUP] HP restored to",
            original_remaining_hp,
        )


if __name__ == "__main__":
    main()