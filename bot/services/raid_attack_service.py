from __future__ import annotations

from dataclasses import dataclass

from bot.core.database import session_scope
from bot.models.boss import Boss
from bot.models.player import Player
from bot.models.raid import Raid
from bot.models.team import Team
from bot.repositories.raid_attack_repository import (
    RaidAttackRepository,
)


@dataclass(frozen=True)
class RaidAttackState:
    attack_id: int

    raid_id: int
    phase_no: int
    boss_id: int

    player_id: int
    team_id: int

    damage: int

    source_message_id: int | None
    image_sha256: str | None


@dataclass(frozen=True)
class RaidAttackRegistrationResult:
    attack: RaidAttackState
    created: bool


class RaidAttackService:
    """
    実際のRaid凸履歴を管理する。

    このPhaseではRaidAttackの記録だけを担当する。
    Boss残HPはまだ変更しない。
    """

    def record_attack(
        self,
        *,
        raid_id: int,
        phase_no: int,
        boss_id: int,
        player_id: int,
        team_id: int,
        damage: int,
        source_message_id: int | None = None,
        image_sha256: str | None = None,
    ) -> RaidAttackRegistrationResult:
        if phase_no not in (
            1,
            2,
            3,
        ):
            raise ValueError(
                (
                    "RaidAttackで記録できる"
                    "phase_noは1～3です: "
                    f"{phase_no}"
                )
            )

        if damage < 0:
            raise ValueError(
                (
                    "damageは0以上である必要があります: "
                    f"{damage}"
                )
            )

        if (
            image_sha256 is not None
            and len(image_sha256) != 64
        ):
            raise ValueError(
                "image_sha256は64文字である必要があります"
            )

        with session_scope() as session:
            repository = RaidAttackRepository(
                session
            )

            # --------------------------------
            # 二重登録防止
            # --------------------------------

            if source_message_id is not None:
                existing = (
                    repository
                    .get_by_source_message_id(
                        source_message_id
                    )
                )

                if existing is not None:
                    return (
                        RaidAttackRegistrationResult(
                            attack=self._to_state(
                                existing
                            ),
                            created=False,
                        )
                    )

            if image_sha256 is not None:
                existing = (
                    repository
                    .get_by_image_sha256(
                        image_sha256
                    )
                )

                if existing is not None:
                    return (
                        RaidAttackRegistrationResult(
                            attack=self._to_state(
                                existing
                            ),
                            created=False,
                        )
                    )

            # --------------------------------
            # Raid
            # --------------------------------

            raid = session.get(
                Raid,
                raid_id,
            )

            if raid is None:
                raise ValueError(
                    (
                        "Raidが存在しません: "
                        f"raid_id={raid_id}"
                    )
                )

            # --------------------------------
            # Boss
            # --------------------------------

            boss = session.get(
                Boss,
                boss_id,
            )

            if boss is None:
                raise ValueError(
                    (
                        "Bossが存在しません: "
                        f"boss_id={boss_id}"
                    )
                )

            if boss.raid_id != raid_id:
                raise ValueError(
                    (
                        "Bossが指定Raidに属していません: "
                        f"raid_id={raid_id}, "
                        f"boss_id={boss_id}"
                    )
                )

            # --------------------------------
            # Player
            # --------------------------------

            player = session.get(
                Player,
                player_id,
            )

            if player is None:
                raise ValueError(
                    (
                        "Playerが存在しません: "
                        f"player_id={player_id}"
                    )
                )

            # --------------------------------
            # Team
            # --------------------------------

            team = session.get(
                Team,
                team_id,
            )

            if team is None:
                raise ValueError(
                    (
                        "Teamが存在しません: "
                        f"team_id={team_id}"
                    )
                )

            if team.player_id != player_id:
                raise ValueError(
                    (
                        "Teamが指定Playerに"
                        "属していません: "
                        f"player_id={player_id}, "
                        f"team_id={team_id}"
                    )
                )

            # --------------------------------
            # RaidAttack作成
            # --------------------------------

            attack = repository.create(
                raid_id=raid_id,
                phase_no=phase_no,
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

            return RaidAttackRegistrationResult(
                attack=self._to_state(
                    attack
                ),
                created=True,
            )

    def list_by_raid(
        self,
        raid_id: int,
    ) -> tuple[RaidAttackState, ...]:
        with session_scope() as session:
            repository = RaidAttackRepository(
                session
            )

            attacks = (
                repository.list_by_raid_id(
                    raid_id
                )
            )

            return tuple(
                self._to_state(
                    attack
                )
                for attack in attacks
            )

    @staticmethod
    def _to_state(
        attack,
    ) -> RaidAttackState:
        return RaidAttackState(
            attack_id=attack.id,
            raid_id=attack.raid_id,
            phase_no=attack.phase_no,
            boss_id=attack.boss_id,
            player_id=attack.player_id,
            team_id=attack.team_id,
            damage=attack.damage,
            source_message_id=(
                attack.source_message_id
            ),
            image_sha256=(
                attack.image_sha256
            ),
        )