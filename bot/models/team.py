from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


class Team(Base):
    __tablename__ = "teams"

    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "team_name",
            name="uq_team_player_name",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        index=True,
    )

    team_name: Mapped[str] = mapped_column(
        String(100),
    )

    memo: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )

    player: Mapped["Player"] = relationship(
        back_populates="teams",
    )

    damage_records: Mapped[list["DamageRecord"]] = relationship(
        back_populates="team",
    )