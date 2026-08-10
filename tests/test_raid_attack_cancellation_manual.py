from sqlalchemy import (
    delete,
    select,
)

from bot.core.database import session_scope
from bot.models.raid_attack import RaidAttack
from bot.models.raid_attack_cancellation import (
    RaidAttackCancellation,
)
from bot.services.raid_attack_cancellation_service import (
    RaidAttackCancellationService,
)


def main() -> None:
    service = (
        RaidAttackCancellationService()
    )

    attack_id: int | None = None

    # --------------------------------
    # まだ取消されていない
    # RaidAttackを1件探す
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

            if cancellation is None:
                attack_id = attack.id
                break

    if attack_id is None:
        print(
            "[SKIP] "
            "取消テストに使える"
            "RaidAttackがありません。"
        )
        return

    print(
        "test RaidAttack ID =",
        attack_id,
    )

    try:
        # --------------------------------
        # 1回目
        # --------------------------------

        result = service.cancel(
            raid_attack_id=attack_id,
            cancelled_by_discord_id=(
                "manual-test"
            ),
            reason=(
                "manual cancellation test"
            ),
        )

        assert (
            result.already_cancelled
            is False
        )

        assert service.is_cancelled(
            attack_id
        )

        print(
            "[OK] cancellation created"
        )

        print(
            "Cancellation ID =",
            result.cancellation_id,
        )

        print(
            "Damage =",
            f"{result.damage:,}",
        )

        # --------------------------------
        # 2回目
        #
        # 二重取消にならないこと
        # --------------------------------

        second = service.cancel(
            raid_attack_id=attack_id,
            cancelled_by_discord_id=(
                "manual-test"
            ),
        )

        assert (
            second.already_cancelled
            is True
        )

        assert (
            second.cancellation_id
            == result.cancellation_id
        )

        print(
            "[OK] duplicate cancellation prevented"
        )

        print(
            "RaidAttack Cancellation TEST OK"
        )

    finally:
        # --------------------------------
        # テストで作った取消履歴だけ削除
        #
        # RaidAttack本体には触れない
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

        print(
            "[CLEANUP] "
            "test cancellation removed"
        )

if __name__ == "__main__":
    main()