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
from bot.repositories.raid_attack_cancellation_repository import (
    RaidAttackCancellationRepository,
)
from bot.repositories.raid_boss_progress_repository import (
    RaidBossProgressRepository,
)
from bot.services.raid_attack_service import (
    RaidAttackState,
)


@dataclass(frozen=True)
class RaidAttackProgressResult:
    """
    実凸登録とBoss HP更新結果。
    """

    attack: RaidAttackState

    created: bool

    boss_id: int
    boss_no: int
    phase_no: int

    previous_remaining_hp: int | None
    remaining_hp: int | None

    applied_damage: int

    @property
    def defeated(self) -> bool:
        return (
            self.remaining_hp is not None
            and self.remaining_hp <= 0
        )


class RaidAttackProgressService:
    """
    実際の1凸を記録し、
    同じトランザクション内で
    Boss残HPを減算する。
    """

    def record_and_apply(
        self,
        *,
        raid_id: int,
        boss_id: int,
        player_id: int,
        team_id: int,
        damage: int,
        source_message_id: int | None = None,
        image_sha256: str | None = None,
        expected_phase_no: int | None = None,
    ) -> RaidAttackProgressResult:
        # --------------------------------
        # 基本Validation
        # --------------------------------

        if damage < 0:
            raise ValueError(
                (
                    "damageは0以上である"
                    "必要があります: "
                    f"{damage}"
                )
            )

        if (
            image_sha256 is not None
            and len(image_sha256) != 64
        ):
            raise ValueError(
                (
                    "image_sha256は"
                    "64文字である必要があります"
                )
            )

        # --------------------------------
        # 1 transaction
        # --------------------------------

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

            progress_repository = (
                RaidBossProgressRepository(
                    session
                )
            )

            # --------------------------------
            # 重複確認
            #
            # ここで既存なら
            # HPは絶対に変更しない。
            # --------------------------------

            existing = None

            if source_message_id is not None:
                existing = (
                    attack_repository
                    .get_by_source_message_id(
                        source_message_id
                    )
                )

            if (
                existing is None
                and image_sha256 is not None
            ):
                existing = (
                    attack_repository
                    .get_by_image_sha256(
                        image_sha256
                    )
                )

            # --------------------------------
            # 同じTeamの実凸済み確認
            #
            # source_message_id / image_sha256
            # がNoneのコマンド登録でも、
            # 同一Raidで同じTeamを
            # 二重登録させない。
            #
            # Cancellation済みRaidAttackは
            # 無効なので再実凸可能。
            # --------------------------------

            team_attacks = (
                attack_repository
                .list_by_raid_and_team(
                    raid_id=raid_id,
                    team_id=team_id,
                )
            )

            active_team_attacks = [
                attack
                for attack in team_attacks
                if not cancellation_repository
                .is_cancelled(
                    attack.id
                )
            ]

            if active_team_attacks:
                active_attack = (
                    active_team_attacks[0]
                )

                raise ValueError(
                    (
                        "このTeamはすでに"
                        "実凸済みです: "
                        f"team_id={team_id}, "
                        "raid_attack_id="
                        f"{active_attack.id}"
                    )
                )

            if existing is not None:
                if existing.raid_id != raid_id:
                    raise ValueError(
                        (
                            "重複RaidAttackのraid_idが"
                            "一致しません: "
                            f"existing={existing.raid_id}, "
                            f"requested={raid_id}"
                        )
                    )

                return RaidAttackProgressResult(
                    attack=self._to_attack_state(
                        existing
                    ),
                    created=False,
                    boss_id=existing.boss_id,
                    boss_no=self._get_boss_no(
                        session=session,
                        boss_id=existing.boss_id,
                    ),
                    phase_no=(
                        existing.phase_no
                    ),
                    previous_remaining_hp=None,
                    remaining_hp=None,
                    applied_damage=0,
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

            # Phase 4 = Final
            if raid.current_phase > 3:
                raise ValueError(
                    (
                        "最終Phaseでは"
                        "RaidAttack/HP管理を"
                        "行いません: "
                        f"current_phase="
                        f"{raid.current_phase}"
                    )
                )

            current_phase = (
                raid.current_phase
            )

            # --------------------------------
            # Screenshot解析時のPhaseと
            # 現在Phaseが一致するか確認
            # --------------------------------

            if (
                expected_phase_no is not None
                and current_phase
                != expected_phase_no
            ):
                raise ValueError(
                    (
                        "スクリーンショット解析後に"
                        "Raid Phaseが変化しました: "
                        f"expected_phase="
                        f"{expected_phase_no}, "
                        f"current_phase="
                        f"{current_phase}"
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
                        "Bossが指定Raidに"
                        "属していません: "
                        f"raid_id={raid_id}, "
                        f"boss_id={boss_id}"
                    )
                )

            # --------------------------------
            # 現在PhaseのBossPhase
            # --------------------------------

            phase = (
                progress_repository.get_phase(
                    boss_id=boss.id,
                    phase_no=current_phase,
                )
            )

            if phase is None:
                raise ValueError(
                    (
                        "現在PhaseのBossPhaseが"
                        "設定されていません: "
                        f"boss_id={boss.id}, "
                        f"phase_no={current_phase}"
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
            # 現在HP
            # --------------------------------

            progress = (
                progress_repository
                .get_or_create_progress(
                    phase
                )
            )

            previous_remaining_hp = (
                progress.remaining_hp
            )

            if previous_remaining_hp <= 0:
                raise ValueError(
                    (
                        "このBossはすでに"
                        "撃破されています: "
                        f"boss_id={boss.id}, "
                        f"phase_no={current_phase}"
                    )
                )

            # --------------------------------
            # RaidAttack作成
            #
            # まだcommitされない。
            # --------------------------------

            attack = (
                attack_repository.create(
                    raid_id=raid.id,
                    phase_no=current_phase,
                    boss_id=boss.id,
                    player_id=player.id,
                    team_id=team.id,
                    damage=damage,
                    source_message_id=(
                        source_message_id
                    ),
                    image_sha256=(
                        image_sha256
                    ),
                )
            )

            # --------------------------------
            # Boss HP減算
            # --------------------------------

            remaining_hp = max(
                0,
                previous_remaining_hp
                - damage,
            )

            applied_damage = (
                previous_remaining_hp
                - remaining_hp
            )

            progress_repository.set_remaining_hp(
                progress=progress,
                remaining_hp=remaining_hp,
            )

            # session_scopeを抜けると
            # RaidAttack + HPが同時commitされる。

            return RaidAttackProgressResult(
                attack=self._to_attack_state(
                    attack
                ),
                created=True,
                boss_id=boss.id,
                boss_no=boss.boss_no,
                phase_no=current_phase,
                previous_remaining_hp=(
                    previous_remaining_hp
                ),
                remaining_hp=remaining_hp,
                applied_damage=(
                    applied_damage
                ),
            )

    @staticmethod
    def _to_attack_state(
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

    @staticmethod
    def _get_boss_no(
        *,
        session,
        boss_id: int,
    ) -> int:
        boss = session.get(
            Boss,
            boss_id,
        )

        if boss is None:
            raise ValueError(
                (
                    "RaidAttackが参照する"
                    "Bossが存在しません: "
                    f"boss_id={boss_id}"
                )
            )

        return boss.boss_no
