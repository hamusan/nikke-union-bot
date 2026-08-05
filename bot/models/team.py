from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


class Team(Base):
    """Playerが所有する編成。"""

    __tablename__ = "teams"

    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "team_no",
            name="uq_team_player_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        index=True,
    )

    team_no: Mapped[int] = mapped_column(
        Integer,
    )

    team_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    memo: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )

    player: Mapped["Player"] = relationship(
        back_populates="teams",
    )

    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
        order_by="TeamMember.position",
    )

    damage_records: Mapped[list["DamageRecord"]] = relationship(
        back_populates="team",
    )