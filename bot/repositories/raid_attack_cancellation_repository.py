from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from bot.models.raid_attack_cancellation import (
    RaidAttackCancellation,
)


class RaidAttackCancellationRepository:
    """RaidAttack取消履歴のDB操作。"""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

    def get_by_attack_id(
        self,
        raid_attack_id: int,
    ) -> RaidAttackCancellation | None:
        """指定RaidAttackの取消履歴を取得する。"""

        return self.session.scalar(
            select(
                RaidAttackCancellation
            )
            .where(
                RaidAttackCancellation
                .raid_attack_id
                == raid_attack_id
            )
        )

    def create(
        self,
        raid_attack_id: int,
        cancelled_by_discord_id: (
            str | None
        ) = None,
        reason: str | None = None,
    ) -> RaidAttackCancellation:
        """RaidAttackの取消履歴を作成する。"""

        cancellation = (
            RaidAttackCancellation(
                raid_attack_id=raid_attack_id,
                cancelled_by_discord_id=(
                    cancelled_by_discord_id
                ),
                reason=reason,
            )
        )

        self.session.add(
            cancellation
        )

        self.session.flush()

        return cancellation

    def is_cancelled(
        self,
        raid_attack_id: int,
    ) -> bool:
        """RaidAttackが取消済みか返す。"""

        return (
            self.get_by_attack_id(
                raid_attack_id
            )
            is not None
        )