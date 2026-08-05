from __future__ import annotations

from sqlalchemy import (
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


class TeamMember(Base):
    """編成に所属するNIKKEを表す。"""

    __tablename__ = "team_members"

    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "position",
            name="uq_team_member_position",
        ),
        UniqueConstraint(
            "team_id",
            "character_id",
            name="uq_team_member_character",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"),
        index=True,
    )

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id"),
        index=True,
    )

    position: Mapped[int]

    team: Mapped["Team"] = relationship(
        back_populates="members",
    )

    character: Mapped["Character"] = relationship(
        back_populates="team_members",
    )