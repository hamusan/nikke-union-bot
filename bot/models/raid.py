from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


class Raid(Base):
    __tablename__ = "raids"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
    )

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )

    bosses: Mapped[list["Boss"]] = relationship(
        back_populates="raid",
        cascade="all, delete-orphan",
    )