from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from bot.models.base import Base


class RaidBossProgress(Base):
    """
    Raid中のBossPhase残HP。

    BossPhase.max_hp:
        最大HP・設定値

    RaidBossProgress.remaining_hp:
        現在の実HP
    """

    __tablename__ = (
        "raid_boss_progress"
    )

    __table_args__ = (
        UniqueConstraint(
            "boss_phase_id",
            name=(
                "uq_raid_boss_progress_"
                "boss_phase"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    boss_phase_id: Mapped[int] = (
        mapped_column(
            ForeignKey(
                "boss_phases.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        )
    )

    remaining_hp: Mapped[int] = (
        mapped_column(
            BigInteger,
            nullable=False,
        )
    )

    updated_at: Mapped[datetime] = (
        mapped_column(
            DateTime(
                timezone=True
            ),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        )
    )