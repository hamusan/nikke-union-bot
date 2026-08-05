from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


class Raid(Base):
    """ユニオンレイド開催単位。"""

    __tablename__ = "raids"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )

    bosses: Mapped[list["Boss"]] = relationship(
        back_populates="raid",
        cascade="all, delete-orphan",
    )