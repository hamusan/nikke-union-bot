from __future__ import annotations

from dataclasses import dataclass

from bot.services.raid_attack_cancellation_service import (
    RaidAttackCancellationResult,
    RaidAttackCancellationService,
)
from bot.services.raid_rebuild_service import (
    RaidRebuildResult,
    RaidRebuildService,
)


@dataclass(
    frozen=True
)
class RaidAttackCancellationCoordinatorResult:
    """
    実凸取消 + Raid再構築結果。
    """

    cancellation: RaidAttackCancellationResult
    rebuild: RaidRebuildResult


class RaidAttackCancellationCoordinatorService:
    """
    RaidAttackを取り消して、
    Raid全体を再構築するService。
    """

    def __init__(
        self,
    ) -> None:
        self._cancellation_service = (
            RaidAttackCancellationService()
        )

        self._rebuild_service = (
            RaidRebuildService()
        )

    def cancel_attack(
        self,
        raid_attack_id: int,
        cancelled_by_discord_id: (
            str | None
        ) = None,
        reason: str | None = None,
    ) -> RaidAttackCancellationCoordinatorResult:
        """
        RaidAttackを取消済みにし、
        有効なRaidAttack履歴から
        Raid Phase・Boss HPを再構築する。

        すでに取消済みの場合でも
        rebuild()は必ず実行する。
        """

        cancellation = (
            self._cancellation_service.cancel(
                raid_attack_id=(
                    raid_attack_id
                ),
                cancelled_by_discord_id=(
                    cancelled_by_discord_id
                ),
                reason=reason,
            )
        )

        # --------------------------------
        # 取消済みだった場合も実行する。
        #
        # 取消保存直後にBotが停止した場合など、
        # HP再構築だけ未実行になった状態を
        # 再試行で復旧できるようにする。
        # --------------------------------

        rebuild = (
            self._rebuild_service.rebuild(
                cancellation.raid_id
            )
        )

        return (
            RaidAttackCancellationCoordinatorResult(
                cancellation=cancellation,
                rebuild=rebuild,
            )
        )