from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from bot.models.base import Base


class RaidAttack(Base):
    """
    ユニオンレイドで実際に行われた1凸。

    DamageRecord:
        最適化に使用するDamage実績。

    RaidAttack:
        実際のRaid進行に使用する不変の凸履歴。
    """

    __tablename__ = "raid_attacks"

    __table_args__ = (
        CheckConstraint(
            "phase_no >= 1 AND phase_no <= 3",
            name="ck_raid_attacks_phase_no",
        ),
        CheckConstraint(
            "damage >= 0",
            name="ck_raid_attacks_damage",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    raid_id: Mapped[int] = mapped_column(
        ForeignKey(
            "raids.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    phase_no: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )

    boss_id: Mapped[int] = mapped_column(
        ForeignKey(
            "bosses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    player_id: Mapped[int] = mapped_column(
        ForeignKey(
            "players.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    team_id: Mapped[int] = mapped_column(
        ForeignKey(
            "teams.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    damage: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # Discordの元メッセージ。
    #
    # 同じ確認処理が二重に走っても
    # 同じRaidAttackを二重登録しないために使用する。
    source_message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        unique=True,
        index=True,
    )

    # 元スクリーンショットのSHA-256。
    #
    # 同じ画像の再登録防止に使用する。
    image_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        server_default=func.now(),
    )