from __future__ import annotations

from sqlalchemy import (
    delete,
    select,
)

from bot.core.database import session_scope
from bot.models.raid_attack import (
    RaidAttack,
)
from bot.models.raid_attack_cancellation import (
    RaidAttackCancellation,
)
from bot.services.raid_attack_cancellation_coordinator_service import (
    RaidAttackCancellationCoordinatorService,
)
from bot.services.raid_rebuild_service import (
    RaidRebuildService,
)


def main() -> None:
    coordinator = (
        RaidAttackCancellationCoordinatorService()
    )

    rebuild_service = (
        RaidRebuildService()
    )

    attack_id: int | None = None
    raid_id: int | None = None

    # --------------------------------
    # 取消されていないRaidAttackを探す
    # --------------------------------

    with session_scope() as session:
        attacks = list(
            session.scalars(
                select(
                    RaidAttack
                )
                .order_by(
                    RaidAttack.id.desc()
                )
            ).all()
        )

        for attack in attacks:
            cancellation = session.scalar(
                select(
                    RaidAttackCancellation
                )
                .where(
                    RaidAttackCancellation
                    .raid_attack_id
                    == attack.id
                )
            )

            if cancellation is not None:
                continue

            attack_id = attack.id
            raid_id = attack.raid_id
            break

    if (
        attack_id is None
        or raid_id is None
    ):
        print(
            "[SKIP] "
            "取消可能なRaidAttackがありません。"
        )
        return

    print(
        "Raid ID =",
        raid_id,
    )

    print(
        "Test RaidAttack ID =",
        attack_id,
    )

    # --------------------------------
    # 取消前の正しい再構築状態
    # --------------------------------

    before = rebuild_service.preview(
        raid_id
    )

    print()
    print(
        "Before Phase =",
        before.current_phase,
    )

    print(
        "Before Active attacks =",
        before.active_attack_count,
    )

    print(
        "Before Cancelled attacks =",
        before.cancelled_attack_count,
    )

    try:
        # --------------------------------
        # 1回目の取消
        # --------------------------------

        result = coordinator.cancel_attack(
            raid_attack_id=attack_id,
            cancelled_by_discord_id=(
                "manual-test"
            ),
            reason=(
                "coordinator manual test"
            ),
        )

        cancellation = (
            result.cancellation
        )

        rebuilt = (
            result.rebuild
        )

        assert (
            cancellation.already_cancelled
            is False
        )

        assert (
            rebuilt.active_attack_count
            == before.active_attack_count
            - 1
        )

        assert (
            rebuilt.cancelled_attack_count
            == before.cancelled_attack_count
            + 1
        )

        print()
        print(
            "[OK] cancellation created"
        )

        print(
            "Cancellation ID =",
            cancellation.cancellation_id,
        )

        print(
            "After Phase =",
            rebuilt.current_phase,
        )

        print(
            "After Active attacks =",
            rebuilt.active_attack_count,
        )

        print(
            "After Cancelled attacks =",
            rebuilt.cancelled_attack_count,
        )

        print(
            "After Applied attacks =",
            rebuilt.applied_attack_count,
        )

        print(
            "After Blocked attacks =",
            rebuilt.blocked_attack_count,
        )

        # --------------------------------
        # 2回目
        #
        # 取消を二重作成しないが、
        # rebuildは再実行されることを確認。
        # --------------------------------

        second = coordinator.cancel_attack(
            raid_attack_id=attack_id,
            cancelled_by_discord_id=(
                "manual-test"
            ),
        )

        assert (
            second.cancellation
            .already_cancelled
            is True
        )

        assert (
            second.cancellation
            .cancellation_id
            == cancellation.cancellation_id
        )

        assert (
            second.rebuild.current_phase
            == rebuilt.current_phase
        )

        assert (
            second.rebuild
            .active_attack_count
            == rebuilt.active_attack_count
        )

        assert (
            second.rebuild
            .cancelled_attack_count
            == rebuilt.cancelled_attack_count
        )

        print(
            "[OK] duplicate cancellation prevented"
        )

        print(
            "[OK] rebuild retry succeeded"
        )

    finally:
        # --------------------------------
        # テスト取消だけ削除
        # --------------------------------

        with session_scope() as session:
            session.execute(
                delete(
                    RaidAttackCancellation
                )
                .where(
                    RaidAttackCancellation
                    .raid_attack_id
                    == attack_id
                )
            )

        # --------------------------------
        # 元のRaidAttack一覧から
        # Raidを再構築して完全復元
        # --------------------------------

        restored = (
            rebuild_service.rebuild(
                raid_id
            )
        )

        print()
        print(
            "[CLEANUP] "
            "test cancellation removed"
        )

        print(
            "[CLEANUP] "
            "Raid rebuilt"
        )

        # 取消前の計算結果と同じか確認
        assert (
            restored.current_phase
            == before.current_phase
        )

        assert (
            restored.active_attack_count
            == before.active_attack_count
        )

        assert (
            restored.cancelled_attack_count
            == before.cancelled_attack_count
        )

        assert (
            restored.applied_attack_count
            == before.applied_attack_count
        )

        assert (
            restored.blocked_attack_ids
            == before.blocked_attack_ids
        )

        assert (
            restored.bosses
            == before.bosses
        )

        print(
            "[OK] original Raid state restored"
        )

    print()
    print(
        "RaidAttack Cancellation "
        "Coordinator TEST OK"
    )


if __name__ == "__main__":
    main()