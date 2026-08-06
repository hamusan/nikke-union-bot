from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    func,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from bot.models.base import Base


class OptimizationSession(Base):
    """
    /optimize の継続更新状態。

    Bot再起動後でも、
    Activeな最適化メッセージを
    復元できるようにDBへ保存する。
    """

    __tablename__ = "optimization_sessions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # 1チャンネルにつき1セッション
    channel_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        unique=True,
        index=True,
    )

    # Botが更新し続けるDiscordメッセージ
    message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    raid_id: Mapped[int] = mapped_column(
        ForeignKey("raids.id"),
        nullable=False,
        index=True,
    )

    interval_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default=text("5"),
    )

    # /optimize を開始したDiscord User
    started_by_discord_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
    )