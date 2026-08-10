from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from bot.core.database import session_scope
from bot.models.boss import Boss
from bot.models.boss_phase import BossPhase
from bot.models.raid import Raid
from bot.models.raid_attack import RaidAttack
from bot.models.raid_attack_cancellation import (
    RaidAttackCancellation,
)
from bot.models.raid_boss_progress import (
    RaidBossProgress,
)


BOSS_NOS = (
    1,
    2,
    3,
    4,
    5,
)

PHASE_NOS = (
    1,
    2,
    3,
)

FINAL_PHASE = 4


@dataclass(
    frozen=True
)
class RaidRebuildBossState:
    """再構築後のBossPhase HP。"""

    boss_id: int
    boss_no: int

    phase_no: int

    max_hp: int
    remaining_hp: int


@dataclass(
    frozen=True
)
class RaidRebuildResult:
    """Raid再構築結果。"""

    raid_id: int

    current_phase: int
    final_reached: bool

    total_attack_count: int
    active_attack_count: int
    cancelled_attack_count: int

    applied_attack_count: int

    blocked_attack_ids: tuple[
        int,
        ...
    ]

    bosses: tuple[
        RaidRebuildBossState,
        ...
    ]

    @property
    def blocked_attack_count(
        self,
    ) -> int:
        return len(
            self.blocked_attack_ids
        )


class RaidRebuildService:
    """
    RaidAttack履歴から
    Raid PhaseとBoss残HPを再構築する。

    RaidAttackCancellationが存在する
    RaidAttackは無効として扱う。
    """

    def preview(
        self,
        raid_id: int,
    ) -> RaidRebuildResult:
        """
        再構築結果だけ計算する。

        DBのPhase・HPは変更しない。
        """

        if raid_id <= 0:
            raise ValueError(
                "raid_id must be greater than zero."
            )

        with session_scope() as session:
            return self._calculate(
                session=session,
                raid_id=raid_id,
            )

    def rebuild(
        self,
        raid_id: int,
    ) -> RaidRebuildResult:
        """
        RaidAttack履歴から状態を再計算し、
        DBへ反映する。
        """

        if raid_id <= 0:
            raise ValueError(
                "raid_id must be greater than zero."
            )

        with session_scope() as session:
            result = self._calculate(
                session=session,
                raid_id=raid_id,
            )

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
            # Raid Phase
            # --------------------------------

            raid.current_phase = (
                result.current_phase
            )

            # --------------------------------
            # BossPhase取得
            # --------------------------------

            phases = list(
                session.scalars(
                    select(
                        BossPhase
                    )
                    .join(
                        Boss,
                        Boss.id
                        == BossPhase.boss_id,
                    )
                    .where(
                        Boss.raid_id
                        == raid_id
                    )
                    .where(
                        BossPhase.phase_no.in_(
                            PHASE_NOS
                        )
                    )
                ).all()
            )

            phase_by_key = {
                (
                    phase.boss_id,
                    phase.phase_no,
                ): phase
                for phase in phases
            }

            phase_ids = [
                phase.id
                for phase in phases
            ]

            # --------------------------------
            # 既存Progress取得
            # --------------------------------

            progress_by_phase_id: dict[
                int,
                RaidBossProgress,
            ] = {}

            if phase_ids:
                progresses = list(
                    session.scalars(
                        select(
                            RaidBossProgress
                        )
                        .where(
                            RaidBossProgress
                            .boss_phase_id
                            .in_(
                                phase_ids
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
            # 再構築HPを反映
            # --------------------------------

            for boss_state in (
                result.bosses
            ):
                phase = phase_by_key.get(
                    (
                        boss_state.boss_id,
                        boss_state.phase_no,
                    )
                )

                if phase is None:
                    raise ValueError(
                        (
                            "BossPhaseが"
                            "見つかりません: "
                            f"boss_id="
                            f"{boss_state.boss_id}, "
                            f"phase_no="
                            f"{boss_state.phase_no}"
                        )
                    )

                progress = (
                    progress_by_phase_id.get(
                        phase.id
                    )
                )

                if progress is None:
                    progress = (
                        RaidBossProgress(
                            boss_phase_id=(
                                phase.id
                            ),
                            remaining_hp=(
                                boss_state
                                .remaining_hp
                            ),
                        )
                    )

                    session.add(
                        progress
                    )

                    progress_by_phase_id[
                        phase.id
                    ] = progress

                else:
                    progress.remaining_hp = (
                        boss_state.remaining_hp
                    )

            session.flush()

            return result

    def _calculate(
        self,
        *,
        session: Session,
        raid_id: int,
    ) -> RaidRebuildResult:
        """
        RaidAttackを再生して
        Raid状態をメモリ上で計算する。
        """

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

        bosses = list(
            session.scalars(
                select(
                    Boss
                )
                .where(
                    Boss.raid_id
                    == raid_id
                )
                .order_by(
                    Boss.boss_no
                )
            ).all()
        )

        boss_by_id = {
            boss.id: boss
            for boss in bosses
        }

        # --------------------------------
        # BossPhase
        # --------------------------------

        phases = list(
            session.scalars(
                select(
                    BossPhase
                )
                .join(
                    Boss,
                    Boss.id
                    == BossPhase.boss_id,
                )
                .where(
                    Boss.raid_id
                    == raid_id
                )
                .where(
                    BossPhase.phase_no.in_(
                        PHASE_NOS
                    )
                )
                .order_by(
                    BossPhase.phase_no,
                    Boss.boss_no,
                )
            ).all()
        )

        phase_by_key = {
            (
                phase.boss_id,
                phase.phase_no,
            ): phase
            for phase in phases
        }

        # 初期状態は全Boss最大HP
        hp_by_key = {
            (
                phase.boss_id,
                phase.phase_no,
            ): phase.max_hp
            for phase in phases
        }

        # --------------------------------
        # RaidAttack
        # --------------------------------

        attacks = list(
            session.scalars(
                select(
                    RaidAttack
                )
                .where(
                    RaidAttack.raid_id
                    == raid_id
                )
                .order_by(
                    RaidAttack.id
                )
            ).all()
        )

        attack_ids = [
            attack.id
            for attack in attacks
        ]

        # --------------------------------
        # Cancellation
        # --------------------------------

        cancelled_ids: set[int] = set()

        if attack_ids:
            cancelled_ids = set(
                session.scalars(
                    select(
                        RaidAttackCancellation
                        .raid_attack_id
                    )
                    .where(
                        RaidAttackCancellation
                        .raid_attack_id
                        .in_(
                            attack_ids
                        )
                    )
                ).all()
            )

        active_attacks = [
            attack
            for attack in attacks
            if attack.id
            not in cancelled_ids
        ]

        # --------------------------------
        # Phase 1から順番に再生
        # --------------------------------

        current_phase = 1

        applied_attack_ids: list[
            int
        ] = []

        for phase_no in PHASE_NOS:
            if current_phase != phase_no:
                break

            phase_attacks = [
                attack
                for attack
                in active_attacks
                if attack.phase_no
                == phase_no
            ]

            # 同じPhase内では
            # RaidAttack ID順に再生する。
            for attack in phase_attacks:
                boss = boss_by_id.get(
                    attack.boss_id
                )

                if boss is None:
                    raise ValueError(
                        (
                            "RaidAttackが参照する"
                            "Bossが存在しません: "
                            f"attack_id="
                            f"{attack.id}, "
                            f"boss_id="
                            f"{attack.boss_id}"
                        )
                    )

                key = (
                    attack.boss_id,
                    phase_no,
                )

                phase = phase_by_key.get(
                    key
                )

                if phase is None:
                    raise ValueError(
                        (
                            "RaidAttackに対応する"
                            "BossPhaseがありません: "
                            f"attack_id="
                            f"{attack.id}, "
                            f"boss_no="
                            f"{boss.boss_no}, "
                            f"phase_no="
                            f"{phase_no}"
                        )
                    )

                previous_hp = (
                    hp_by_key[
                        key
                    ]
                )

                if previous_hp <= 0:
                    raise ValueError(
                        (
                            "撃破済みBossへの"
                            "RaidAttackが"
                            "履歴に存在します: "
                            f"attack_id="
                            f"{attack.id}, "
                            f"boss_no="
                            f"{boss.boss_no}, "
                            f"phase_no="
                            f"{phase_no}"
                        )
                    )

                hp_by_key[
                    key
                ] = max(
                    0,
                    previous_hp
                    - attack.damage,
                )

                applied_attack_ids.append(
                    attack.id
                )

            # --------------------------------
            # Phase終了判定
            # --------------------------------

            configured_boss_nos: set[
                int
            ] = set()

            all_defeated = True

            for boss in bosses:
                key = (
                    boss.id,
                    phase_no,
                )

                if key not in hp_by_key:
                    continue

                configured_boss_nos.add(
                    boss.boss_no
                )

                if hp_by_key[key] > 0:
                    all_defeated = False

            all_configured = (
                configured_boss_nos
                == set(
                    BOSS_NOS
                )
            )

            if (
                all_configured
                and all_defeated
            ):
                current_phase = (
                    phase_no + 1
                )

                continue

            # このPhaseを突破できないなら
            # 未来PhaseのAttackは適用しない。
            break

        applied_set = set(
            applied_attack_ids
        )

        blocked_attack_ids = tuple(
            attack.id
            for attack
            in active_attacks
            if attack.id
            not in applied_set
        )

        # --------------------------------
        # Boss状態を結果化
        # --------------------------------

        boss_states: list[
            RaidRebuildBossState
        ] = []

        for phase in phases:
            boss = boss_by_id.get(
                phase.boss_id
            )

            if boss is None:
                continue

            key = (
                phase.boss_id,
                phase.phase_no,
            )

            boss_states.append(
                RaidRebuildBossState(
                    boss_id=boss.id,
                    boss_no=boss.boss_no,
                    phase_no=(
                        phase.phase_no
                    ),
                    max_hp=(
                        phase.max_hp
                    ),
                    remaining_hp=(
                        hp_by_key[
                            key
                        ]
                    ),
                )
            )

        boss_states.sort(
            key=lambda state: (
                state.phase_no,
                state.boss_no,
            )
        )

        return RaidRebuildResult(
            raid_id=raid_id,

            current_phase=(
                current_phase
            ),

            final_reached=(
                current_phase
                == FINAL_PHASE
            ),

            total_attack_count=(
                len(attacks)
            ),

            active_attack_count=(
                len(active_attacks)
            ),

            cancelled_attack_count=(
                len(cancelled_ids)
            ),

            applied_attack_count=(
                len(applied_attack_ids)
            ),

            blocked_attack_ids=(
                blocked_attack_ids
            ),

            bosses=tuple(
                boss_states
            ),
        )