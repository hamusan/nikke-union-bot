from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)

    discord_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
    )

    nickname: Mapped[str] = mapped_column(
        String(100),
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )

    teams: Mapped[list["Team"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )