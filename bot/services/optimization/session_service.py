from dataclasses import dataclass

from bot.core.database import session_scope
from bot.repositories.optimization_session_repository import (
    OptimizationSessionRepository,
)


@dataclass(frozen=True)
class OptimizationSessionState:
    """継続最適化Sessionの状態。"""

    id: int

    channel_id: int
    message_id: int | None

    raid_id: int

    interval_minutes: int

    started_by_discord_id: int

    active: bool


class OptimizationSessionService:
    """
    /optimize の永続Sessionを管理する。

    Discord APIには触らず、
    Session状態の保存・取得だけを担当する。
    """

    MIN_INTERVAL_MINUTES = 1
    MAX_INTERVAL_MINUTES = 60

    def get_by_channel(
        self,
        channel_id: int,
    ) -> OptimizationSessionState | None:
        """チャンネルのSessionを取得する。"""

        self._validate_positive_id(
            channel_id,
            "channel_id",
        )

        with session_scope() as session:
            repository = (
                OptimizationSessionRepository(
                    session
                )
            )

            row = repository.get_by_channel_id(
                channel_id
            )

            if row is None:
                return None

            return self._to_state(
                row
            )

    def start(
        self,
        channel_id: int,
        message_id: int,
        raid_id: int,
        interval_minutes: int,
        started_by_discord_id: int,
    ) -> OptimizationSessionState:
        """Sessionを開始または再設定する。"""

        self._validate_positive_id(
            channel_id,
            "channel_id",
        )

        self._validate_positive_id(
            message_id,
            "message_id",
        )

        self._validate_positive_id(
            raid_id,
            "raid_id",
        )

        self._validate_positive_id(
            started_by_discord_id,
            "started_by_discord_id",
        )

        if (
            interval_minutes
            < self.MIN_INTERVAL_MINUTES
            or interval_minutes
            > self.MAX_INTERVAL_MINUTES
        ):
            raise ValueError(
                (
                    "interval_minutesは"
                    f"{self.MIN_INTERVAL_MINUTES}～"
                    f"{self.MAX_INTERVAL_MINUTES}"
                    "で指定してください。"
                )
            )

        with session_scope() as session:
            repository = (
                OptimizationSessionRepository(
                    session
                )
            )

            row = repository.start_or_replace(
                channel_id=channel_id,
                message_id=message_id,
                raid_id=raid_id,
                interval_minutes=(
                    interval_minutes
                ),
                started_by_discord_id=(
                    started_by_discord_id
                ),
            )

            return self._to_state(
                row
            )

    def stop(
        self,
        channel_id: int,
    ) -> OptimizationSessionState | None:
        """Sessionを停止する。"""

        self._validate_positive_id(
            channel_id,
            "channel_id",
        )

        with session_scope() as session:
            repository = (
                OptimizationSessionRepository(
                    session
                )
            )

            row = (
                repository.stop_by_channel_id(
                    channel_id
                )
            )

            if row is None:
                return None

            return self._to_state(
                row
            )

    def list_active(
        self,
    ) -> tuple[
        OptimizationSessionState,
        ...
    ]:
        """active=Trueの全Sessionを取得する。"""

        with session_scope() as session:
            repository = (
                OptimizationSessionRepository(
                    session
                )
            )

            rows = repository.list_active()

            return tuple(
                self._to_state(row)
                for row in rows
            )

    def update_message_id(
        self,
        channel_id: int,
        message_id: int,
    ) -> OptimizationSessionState | None:
        """保存済みMessage IDを更新する。"""

        self._validate_positive_id(
            channel_id,
            "channel_id",
        )

        self._validate_positive_id(
            message_id,
            "message_id",
        )

        with session_scope() as session:
            repository = (
                OptimizationSessionRepository(
                    session
                )
            )

            row = repository.update_message_id(
                channel_id=channel_id,
                message_id=message_id,
            )

            if row is None:
                return None

            return self._to_state(
                row
            )

    def _to_state(
        self,
        row,
    ) -> OptimizationSessionState:
        return OptimizationSessionState(
            id=row.id,

            channel_id=row.channel_id,
            message_id=row.message_id,

            raid_id=row.raid_id,

            interval_minutes=(
                row.interval_minutes
            ),

            started_by_discord_id=(
                row.started_by_discord_id
            ),

            active=row.active,
        )

    def _validate_positive_id(
        self,
        value: int,
        field_name: str,
    ) -> None:
        if value <= 0:
            raise ValueError(
                (
                    f"{field_name}は"
                    "1以上である必要があります。"
                )
            )