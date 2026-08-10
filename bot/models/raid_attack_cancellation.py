from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    ForeignKey,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from bot.models.base import Base


class RaidAttackCancellation(Base):
    """
    RaidAttackの取り消し履歴。

    RaidAttack自体は削除せず、
    このテーブルに行が存在する場合は
    そのRaidAttackを無効扱いにする。
    """

    __tablename__ = "raid_attack_cancellations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    raid_attack_id: Mapped[int] = mapped_column(
        ForeignKey(
            "raid_attacks.id",
            ondelete="CASCADE",
        ),
        unique=True,
        index=True,
        nullable=False,
    )

    cancelled_by_discord_id: Mapped[
        str | None
    ] = mapped_column(
        String(32),
        nullable=True,
    )

    reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(
            timezone.utc
        ),
        nullable=False,
    )