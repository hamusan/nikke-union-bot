from __future__ import annotations

from dataclasses import dataclass

from bot.core.database import session_scope
from bot.repositories.raid_attack_repository import (
    RaidAttackRepository,
)
from bot.repositories.raid_attack_cancellation_repository import (
    RaidAttackCancellationRepository,
)


@dataclass(
    frozen=True
)
class RaidAttackCancellationResult:
    """
    RaidAttack取消処理の結果。
    """

    raid_attack_id: int
    cancellation_id: int

    raid_id: int
    phase_no: int

    boss_id: int
    player_id: int
    team_id: int

    damage: int

    already_cancelled: bool


class RaidAttackCancellationService:
    """
    RaidAttackを取消済みにするService。

    RaidAttack本体は削除しない。

    raid_attack_cancellationsに
    取消履歴を作成することで、
    そのRaidAttackを無効扱いにする。
    """

    def cancel(
        self,
        raid_attack_id: int,
        cancelled_by_discord_id: (
            str | None
        ) = None,
        reason: str | None = None,
    ) -> RaidAttackCancellationResult:
        """
        RaidAttackを取り消す。

        すでに取消済みの場合は
        新しい取消レコードを作らず、
        既存情報を返す。
        """

        if raid_attack_id <= 0:
            raise ValueError(
                "raid_attack_id must be greater than zero."
            )

        normalized_discord_id = (
            cancelled_by_discord_id.strip()
            if cancelled_by_discord_id is not None
            else None
        )

        if normalized_discord_id == "":
            normalized_discord_id = None

        normalized_reason = (
            reason.strip()
            if reason is not None
            else None
        )

        if normalized_reason == "":
            normalized_reason = None

        with session_scope() as session:
            attack_repository = (
                RaidAttackRepository(
                    session
                )
            )

            cancellation_repository = (
                RaidAttackCancellationRepository(
                    session
                )
            )

            attack = (
                attack_repository.get_by_id(
                    raid_attack_id
                )
            )

            if attack is None:
                raise ValueError(
                    (
                        "RaidAttackが存在しません: "
                        f"raid_attack_id={raid_attack_id}"
                    )
                )

            existing = (
                cancellation_repository
                .get_by_attack_id(
                    raid_attack_id
                )
            )

            if existing is not None:
                return (
                    RaidAttackCancellationResult(
                        raid_attack_id=(
                            attack.id
                        ),
                        cancellation_id=(
                            existing.id
                        ),
                        raid_id=(
                            attack.raid_id
                        ),
                        phase_no=(
                            attack.phase_no
                        ),
                        boss_id=(
                            attack.boss_id
                        ),
                        player_id=(
                            attack.player_id
                        ),
                        team_id=(
                            attack.team_id
                        ),
                        damage=(
                            attack.damage
                        ),
                        already_cancelled=True,
                    )
                )

            cancellation = (
                cancellation_repository.create(
                    raid_attack_id=(
                        attack.id
                    ),
                    cancelled_by_discord_id=(
                        normalized_discord_id
                    ),
                    reason=(
                        normalized_reason
                    ),
                )
            )

            return RaidAttackCancellationResult(
                raid_attack_id=(
                    attack.id
                ),
                cancellation_id=(
                    cancellation.id
                ),
                raid_id=(
                    attack.raid_id
                ),
                phase_no=(
                    attack.phase_no
                ),
                boss_id=(
                    attack.boss_id
                ),
                player_id=(
                    attack.player_id
                ),
                team_id=(
                    attack.team_id
                ),
                damage=(
                    attack.damage
                ),
                already_cancelled=False,
            )

    def is_cancelled(
        self,
        raid_attack_id: int,
    ) -> bool:
        """RaidAttackが取消済みか確認する。"""

        if raid_attack_id <= 0:
            return False

        with session_scope() as session:
            repository = (
                RaidAttackCancellationRepository(
                    session
                )
            )

            return repository.is_cancelled(
                raid_attack_id
            )