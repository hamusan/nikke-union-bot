from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from bot.models.optimization_session import (
    OptimizationSession,
)


class OptimizationSessionRepository:
    """OptimizationSessionのDB操作。"""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def get_by_channel_id(
        self,
        channel_id: int,
    ) -> OptimizationSession | None:
        statement = select(
            OptimizationSession
        ).where(
            OptimizationSession.channel_id
            == channel_id
        )

        return self._session.scalar(
            statement
        )

    def list_active(
        self,
    ) -> list[OptimizationSession]:
        statement = (
            select(OptimizationSession)
            .where(
                OptimizationSession.active.is_(
                    True
                )
            )
            .order_by(
                OptimizationSession.id
            )
        )

        return list(
            self._session.scalars(
                statement
            ).all()
        )

    def start_or_replace(
        self,
        channel_id: int,
        message_id: int,
        raid_id: int,
        interval_minutes: int,
        started_by_discord_id: int,
    ) -> OptimizationSession:
        """
        チャンネルのSessionを開始する。

        既存rowがあれば再利用する。
        """

        row = self.get_by_channel_id(
            channel_id
        )

        now = datetime.now()

        if row is None:
            row = OptimizationSession(
                channel_id=channel_id,
                message_id=message_id,
                raid_id=raid_id,
                interval_minutes=(
                    interval_minutes
                ),
                started_by_discord_id=(
                    started_by_discord_id
                ),
                active=True,
                created_at=now,
                updated_at=now,
            )

            self._session.add(
                row
            )

        else:
            row.message_id = message_id
            row.raid_id = raid_id
            row.interval_minutes = (
                interval_minutes
            )
            row.started_by_discord_id = (
                started_by_discord_id
            )
            row.active = True
            row.updated_at = now

        self._session.flush()

        return row

    def stop_by_channel_id(
        self,
        channel_id: int,
    ) -> OptimizationSession | None:
        row = self.get_by_channel_id(
            channel_id
        )

        if row is None:
            return None

        row.active = False
        row.updated_at = datetime.now()

        self._session.flush()

        return row

    def update_message_id(
        self,
        channel_id: int,
        message_id: int,
    ) -> OptimizationSession | None:
        row = self.get_by_channel_id(
            channel_id
        )

        if row is None:
            return None

        row.message_id = message_id
        row.updated_at = datetime.now()

        self._session.flush()

        return row