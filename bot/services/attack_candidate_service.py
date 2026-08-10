from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from bot.core.database import session_scope
from bot.models import DamageRecord
from bot.models.boss import Boss
from bot.models.boss_phase import BossPhase
from bot.models.player import Player
from bot.models.raid import Raid
from bot.models.raid_attack import RaidAttack
from bot.models.raid_attack_cancellation import (
    RaidAttackCancellation,
)
from bot.models.raid_boss_progress import (
    RaidBossProgress,
)
from bot.models.team import Team


@dataclass(
    frozen=True
)
class AttackDamageCandidate:
    """実凸登録に使用できるDamageRecord。"""

    damage_record_id: int

    raid_id: int
    phase_no: int

    boss_id: int
    boss_no: int
    boss_name: str

    team_id: int
    player_id: int

    damage: int

    boss_max_hp: int
    boss_remaining_hp: int


@dataclass(
    frozen=True
)
class AttackCandidateResult:
    """1編成の実凸候補一覧。"""

    raid_id: int
    raid_name: str

    current_phase: int

    team_id: int
    team_no: int

    player_id: int
    player_name: str

    active_raid_attack_id: int | None

    candidates: tuple[
        AttackDamageCandidate,
        ...
    ]

    @property
    def attacked(
        self,
    ) -> bool:
        return (
            self.active_raid_attack_id
            is not None
        )


class AttackCandidateService:
    """
    /attack の実凸ボタン用。

    現在Phaseで使用できる
    DamageRecordを取得する。
    """

    def get_for_team(
        self,
        team_id: int,
    ) -> AttackCandidateResult:
        if team_id <= 0:
            raise ValueError(
                "team_id must be greater than zero."
            )

        with session_scope() as session:
            # --------------------------------
            # Active Raid
            # --------------------------------

            raid = session.scalar(
                select(
                    Raid
                )
                .where(
                    Raid.active.is_(True)
                )
                .order_by(
                    Raid.id.desc()
                )
            )

            if raid is None:
                raise ValueError(
                    "Active Raidがありません。"
                )

            if raid.current_phase not in (
                1,
                2,
                3,
            ):
                raise ValueError(
                    (
                        "現在は最終Phaseです。"
                        "このBotでの実凸管理対象外です。"
                    )
                )

            # --------------------------------
            # Team / Player
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

            if not team.active:
                raise ValueError(
                    (
                        "このTeamは無効です: "
                        f"team_id={team_id}"
                    )
                )

            player = session.get(
                Player,
                team.player_id,
            )

            if player is None:
                raise ValueError(
                    (
                        "Playerが存在しません: "
                        f"player_id={team.player_id}"
                    )
                )

            if not player.active:
                raise ValueError(
                    (
                        "このPlayerは無効です: "
                        f"player_id={player.id}"
                    )
                )

            # --------------------------------
            # このRaidで、このTeamが
            # すでに実凸済みか確認
            # --------------------------------

            cancelled_ids = select(
                RaidAttackCancellation
                .raid_attack_id
            )

            active_attacks = list(
                session.scalars(
                    select(
                        RaidAttack
                    )
                    .where(
                        RaidAttack.raid_id
                        == raid.id
                    )
                    .where(
                        RaidAttack.team_id
                        == team.id
                    )
                    .where(
                        ~RaidAttack.id.in_(
                            cancelled_ids
                        )
                    )
                    .order_by(
                        RaidAttack.id
                    )
                ).all()
            )

            if len(active_attacks) > 1:
                raise RuntimeError(
                    (
                        "同じTeamに複数の"
                        "有効RaidAttackがあります: "
                        f"team_id={team.id}, "
                        f"attack_ids="
                        f"{[
                            attack.id
                            for attack
                            in active_attacks
                        ]}"
                    )
                )

            active_raid_attack_id = (
                active_attacks[0].id
                if active_attacks
                else None
            )

            # --------------------------------
            # 現在PhaseのDamageRecord
            # --------------------------------

            rows = list(
                session.execute(
                    select(
                        DamageRecord,
                        Boss,
                        BossPhase,
                    )
                    .join(
                        Boss,
                        Boss.id
                        == DamageRecord.boss_id,
                    )
                    .join(
                        BossPhase,
                        BossPhase.id
                        == DamageRecord.boss_phase_id,
                    )
                    .where(
                        DamageRecord.team_id
                        == team.id
                    )
                    .where(
                        Boss.raid_id
                        == raid.id
                    )
                    .where(
                        BossPhase.boss_id
                        == Boss.id
                    )
                    .where(
                        BossPhase.phase_no
                        == raid.current_phase
                    )
                    .order_by(
                        Boss.boss_no,
                        DamageRecord.id,
                    )
                ).all()
            )

            # --------------------------------
            # Boss残HP
            # --------------------------------

            boss_phase_ids = {
                phase.id
                for (
                    _record,
                    _boss,
                    phase,
                ) in rows
            }

            progress_by_phase_id: dict[
                int,
                RaidBossProgress,
            ] = {}

            if boss_phase_ids:
                progresses = list(
                    session.scalars(
                        select(
                            RaidBossProgress
                        )
                        .where(
                            RaidBossProgress
                            .boss_phase_id
                            .in_(
                                boss_phase_ids
                            )
                        )
                    ).all()
                )

                progress_by_phase_id = {
                    progress.boss_phase_id:
                        progress
                    for progress
                    in progresses
                }

            # --------------------------------
            # 候補生成
            # --------------------------------

            candidates: list[
                AttackDamageCandidate
            ] = []

            for (
                record,
                boss,
                phase,
            ) in rows:
                progress = (
                    progress_by_phase_id.get(
                        phase.id
                    )
                )

                remaining_hp = (
                    progress.remaining_hp
                    if progress is not None
                    else phase.max_hp
                )

                # 撃破済みBossは候補に出さない。
                if remaining_hp <= 0:
                    continue

                candidates.append(
                    AttackDamageCandidate(
                        damage_record_id=(
                            record.id
                        ),

                        raid_id=raid.id,
                        phase_no=(
                            raid.current_phase
                        ),

                        boss_id=boss.id,
                        boss_no=boss.boss_no,
                        boss_name=boss.name,

                        team_id=team.id,
                        player_id=player.id,

                        damage=record.damage,

                        boss_max_hp=(
                            phase.max_hp
                        ),
                        boss_remaining_hp=(
                            remaining_hp
                        ),
                    )
                )

            return AttackCandidateResult(
                raid_id=raid.id,
                raid_name=raid.name,

                current_phase=(
                    raid.current_phase
                ),

                team_id=team.id,
                team_no=team.team_no,

                player_id=player.id,
                player_name=(
                    player.nickname
                ),

                active_raid_attack_id=(
                    active_raid_attack_id
                ),

                candidates=tuple(
                    candidates
                ),
            )