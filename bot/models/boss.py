from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base

from sqlalchemy import String

class Boss(Base):
    __tablename__ = "bosses"

    __table_args__ = (
        UniqueConstraint(
            "raid_id",
            "boss_no",
            name="uq_boss_raid_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    raid_id: Mapped[int] = mapped_column(
        ForeignKey("raids.id"),
        index=True,
    )

    boss_no: Mapped[int]

    name: Mapped[str] = mapped_column(
        String(100),
    )

    max_hp: Mapped[int] = mapped_column(
        BigInteger,
    )

    current_hp: Mapped[int] = mapped_column(
        BigInteger,
    )

    raid: Mapped["Raid"] = relationship(
        back_populates="bosses",
    )

    damage_records: Mapped[list["DamageRecord"]] = relationship(
        back_populates="boss",
    )

    phases: Mapped[list["BossPhase"]] = relationship(
        back_populates="boss",
        cascade="all, delete-orphan",
        order_by="BossPhase.phase_no",
    )

    boss_key: Mapped[str | None] = mapped_column(
    String(100),
    nullable=True,
    index=True,
    )