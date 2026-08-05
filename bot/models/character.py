from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


class Character(Base):
    """NIKKEキャラクターのマスターデータ。"""

    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
    )

    team_members: Mapped[list["TeamMember"]] = relationship(
        back_populates="character",
    )