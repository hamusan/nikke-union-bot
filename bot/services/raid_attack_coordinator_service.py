from __future__ import annotations

from dataclasses import dataclass

from bot.services.raid_attack_progress_service import (
    RaidAttackProgressResult,
    RaidAttackProgressService,
)
from bot.services.raid_progress_coordinator_service import (
    RaidPhaseAdvanceResult,
    RaidProgressCoordinatorService,
)


@dataclass(frozen=True)
class RaidAttackCoordinatorResult:
    attack: RaidAttackProgressResult
    transition: RaidPhaseAdvanceResult


class RaidAttackCoordinatorService:
    """
    実凸登録からRaid Phase進行判定までを
    まとめて実行する上位Service。
    """

    def __init__(
        self,
    ) -> None:
        self._attack_service = (
            RaidAttackProgressService()
        )

        self._progress_service = (
            RaidProgressCoordinatorService()
        )

    def record_attack(
        self,
        *,
        raid_id: int,
        boss_id: int,
        player_id: int,
        team_id: int,
        damage: int,
        source_message_id: int | None = None,
        image_sha256: str | None = None,
    ) -> RaidAttackCoordinatorResult:
        # RaidAttack作成 + Boss HP減算
        attack_result = (
            self._attack_service.record_and_apply(
                raid_id=raid_id,
                boss_id=boss_id,
                player_id=player_id,
                team_id=team_id,
                damage=damage,
                source_message_id=(
                    source_message_id
                ),
                image_sha256=(
                    image_sha256
                ),
            )
        )

        # Phase進行判定
        #
        # created=Falseでも判定する。
        # HP処理成功後にPhase判定だけ失敗しても、
        # 同じ凸を再処理することで復旧できる。
        transition = (
            self._progress_service
            .evaluate_and_advance(
                raid_id
            )
        )

        return RaidAttackCoordinatorResult(
            attack=attack_result,
            transition=transition,
        )