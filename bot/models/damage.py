from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from bot.models.base import Base


class DamageRecord(Base):
    """ユニオンレイドのダメージ実績。"""

    __tablename__ = "damage_records"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"),
        index=True,
    )

    boss_id: Mapped[int] = mapped_column(
        ForeignKey("bosses.id"),
        index=True,
    )

    # 既存DBとの互換性のため、
    # 現段階ではnullable=True。
    #
    # 新しくOCRから登録するDamageRecordでは
    # 必ずBossPhaseを設定する。
    boss_phase_id: Mapped[int | None] = mapped_column(
        ForeignKey("boss_phases.id"),
        nullable=True,
        index=True,
    )

    damage: Mapped[int] = mapped_column(
        BigInteger
    )

    image_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # 同じ結果スクショの二重登録防止。
    image_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        index=True,
    )

    ocr_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    team: Mapped["Team"] = relationship(
        back_populates="damage_records"
    )

    boss: Mapped["Boss"] = relationship(
        back_populates="damage_records"
    )

    boss_phase: Mapped["BossPhase | None"] = relationship()