from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


class DamageRecord(Base):
    __tablename__ = "damage_records"

    id: Mapped[int] = mapped_column(primary_key=True)

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"),
        index=True,
    )

    boss_id: Mapped[int] = mapped_column(
        ForeignKey("bosses.id"),
        index=True,
    )

    damage: Mapped[int] = mapped_column(
        BigInteger,
    )

    image_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    ocr_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )

    team: Mapped["Team"] = relationship(
        back_populates="damage_records",
    )

    boss: Mapped["Boss"] = relationship(
        back_populates="damage_records",
    )