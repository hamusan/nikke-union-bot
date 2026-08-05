from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from bot.models.base import Base


class BossPhase(Base):
    """BossごとのPhaseと最大HPの対応。"""

    __tablename__ = "boss_phases"

    __table_args__ = (
        UniqueConstraint(
            "boss_id",
            "phase_no",
            name="uq_boss_phase_number",
        ),
        UniqueConstraint(
            "boss_id",
            "max_hp",
            name="uq_boss_phase_max_hp",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    boss_id: Mapped[int] = mapped_column(
        ForeignKey("bosses.id"),
        index=True,
    )

    phase_no: Mapped[int] = mapped_column(
        Integer,
    )

    max_hp: Mapped[int] = mapped_column(
        BigInteger,
    )

    boss: Mapped["Boss"] = relationship(
        back_populates="phases",
    )