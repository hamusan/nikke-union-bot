from collections import defaultdict

from sqlalchemy import select

from bot.core.database import session_scope
from bot.data import get_boss_phase_hp
from bot.models import (
    Boss,
    BossPhase,
    Character,
    Player,
    TeamMember,
)
from bot.services.optimization.assignment import (
    AttackAssignment,
    BossAssignmentSummary,
    UnionAssignmentPlan,
)
from bot.services.optimization.candidate_service import (
    OptimizationCandidateService,
)
from bot.services.optimization.union_solver import (
    UnionOptimizationSolver,
)


class UnionAssignmentService:
    """
    RaidのDamageRecordから、
    「誰が・どの編成で・どのBossを殴るか」
    を生成する。
    """

    def __init__(self) -> None:
        self._candidate_service = (
            OptimizationCandidateService()
        )

        self._solver = (
            UnionOptimizationSolver()
        )

    def build_for_raid(
        self,
        raid_id: int,
        max_attacks_per_player: int = 3,
    ) -> UnionAssignmentPlan:
        """指定Raidの最適攻撃割り当てを生成する。"""

        # --------------------------------
        # 最適化候補
        # --------------------------------

        candidates = (
            self._candidate_service
            .build_for_raid(
                raid_id=raid_id
            )
        )

        if not candidates:
            return UnionAssignmentPlan(
                raid_id=raid_id,
                assignments=(),
                boss_summaries=(),
                attack_count=0,
                total_nominal_damage=0,
                total_effective_damage=0,
            )

        # --------------------------------
        # Boss Masterから正式なHPを取得
        # --------------------------------
        #
        # DBのBossPhase.max_hpは使用しない。
        #
        # DB:
        #   boss_phase_id
        #   phase_no
        #   boss_key
        #
        # Boss Master:
        #   正式なmax_hp
        #
        # という役割分担にする。
        # --------------------------------

        phase_ids = {
            candidate.boss_phase_id
            for candidate in candidates
        }

        with session_scope() as session:
            phase_rows = list(
                session.execute(
                    select(
                        BossPhase.id.label(
                            "boss_phase_id"
                        ),
                        BossPhase.phase_no.label(
                            "phase_no"
                        ),
                        Boss.boss_key.label(
                            "boss_key"
                        ),
                        Boss.name.label(
                            "boss_name"
                        ),
                    )
                    .join(
                        Boss,
                        Boss.id
                        == BossPhase.boss_id,
                    )
                    .where(
                        BossPhase.id.in_(
                            phase_ids
                        )
                    )
                ).all()
            )

        boss_hp_by_phase_id: dict[
            int,
            int,
        ] = {}

        for row in phase_rows:
            # --------------------------------
            # Boss Master未登録Bossは
            # 最適化できない
            # --------------------------------

            if row.boss_key is None:
                raise ValueError(
                    (
                        "Boss Master未登録のBossが"
                        "最適化候補に含まれています: "
                        f"Boss='{row.boss_name}', "
                        f"boss_phase_id="
                        f"{row.boss_phase_id}"
                    )
                )

            # --------------------------------
            # Masterから正式HP取得
            # --------------------------------

            max_hp = get_boss_phase_hp(
                boss_key=row.boss_key,
                phase_no=row.phase_no,
            )

            if max_hp is None:
                raise ValueError(
                    (
                        "Boss MasterにPhase HPが"
                        "登録されていません: "
                        f"Boss='{row.boss_name}', "
                        f"boss_key='{row.boss_key}', "
                        f"Phase={row.phase_no}"
                    )
                )

            boss_hp_by_phase_id[
                row.boss_phase_id
            ] = max_hp

            # --------------------------------
            # DBに存在しないBossPhase検出
            # --------------------------------

            resolved_phase_ids = set(
                boss_hp_by_phase_id
            )

            missing_phase_ids = (
                phase_ids
                - resolved_phase_ids
            )

            if missing_phase_ids:
                raise ValueError(
                    (
                        "最適化候補が参照する"
                        "BossPhaseがDBに存在しません: "
                        f"{sorted(missing_phase_ids)}"
                    )
                )

        # --------------------------------
        # OR-Tools最適化
        # --------------------------------

        result = self._solver.solve(
            candidates=candidates,
            boss_hp_by_phase_id=(
                boss_hp_by_phase_id
            ),
            max_attacks_per_player=(
                max_attacks_per_player
            ),
        )

        if not result.selected_candidates:
            return UnionAssignmentPlan(
                raid_id=raid_id,
                assignments=(),
                boss_summaries=(),
                attack_count=0,
                total_nominal_damage=0,
                total_effective_damage=0,
            )

        # --------------------------------
        # 表示用データをまとめて取得
        # --------------------------------

        player_ids = {
            candidate.player_id
            for candidate
            in result.selected_candidates
        }

        team_ids = {
            candidate.team_id
            for candidate
            in result.selected_candidates
        }

        boss_ids = {
            candidate.boss_id
            for candidate
            in result.selected_candidates
        }

        with session_scope() as session:
            players = list(
                session.scalars(
                    select(Player)
                    .where(
                        Player.id.in_(
                            player_ids
                        )
                    )
                ).all()
            )

            bosses = list(
                session.scalars(
                    select(Boss)
                    .where(
                        Boss.id.in_(
                            boss_ids
                        )
                    )
                ).all()
            )

            member_rows = list(
                session.execute(
                    select(
                        TeamMember.team_id,
                        TeamMember.position,
                        TeamMember.character_id,
                    )
                    .where(
                        TeamMember.team_id.in_(
                            team_ids
                        )
                    )
                    .order_by(
                        TeamMember.team_id,
                        TeamMember.position,
                    )
                ).all()
            )

            character_ids = {
                row.character_id
                for row in member_rows
            }

            characters = list(
                session.scalars(
                    select(Character)
                    .where(
                        Character.id.in_(
                            character_ids
                        )
                    )
                ).all()
            )

        # --------------------------------
        # Map生成
        # --------------------------------

        player_name_by_id = {
            player.id: player.nickname
            for player in players
        }

        boss_name_by_id = {
            boss.id: boss.name
            for boss in bosses
        }

        character_name_by_id = {
            character.id: character.name
            for character in characters
        }

        team_character_names: dict[
            int,
            list[str],
        ] = defaultdict(list)

        for row in member_rows:
            character_name = (
                character_name_by_id.get(
                    row.character_id
                )
            )

            if character_name is None:
                continue

            team_character_names[
                row.team_id
            ].append(
                character_name
            )

        # --------------------------------
        # AttackAssignment生成
        # --------------------------------

        assignments: list[
            AttackAssignment
        ] = []

        for candidate in (
            result.selected_candidates
        ):
            player_name = (
                player_name_by_id.get(
                    candidate.player_id,
                    f"Player {candidate.player_id}",
                )
            )

            boss_name = (
                boss_name_by_id.get(
                    candidate.boss_id,
                    f"Boss {candidate.boss_id}",
                )
            )

            character_names = tuple(
                team_character_names.get(
                    candidate.team_id,
                    [],
                )
            )

            assignment = AttackAssignment(
                damage_record_id=(
                    candidate.damage_record_id
                ),

                player_id=(
                    candidate.player_id
                ),

                player_name=(
                    player_name
                ),

                team_id=(
                    candidate.team_id
                ),

                team_no=(
                    candidate.team_no
                ),

                character_names=(
                    character_names
                ),

                boss_id=(
                    candidate.boss_id
                ),

                boss_name=(
                    boss_name
                ),

                boss_phase_id=(
                    candidate.boss_phase_id
                ),

                phase_no=(
                    candidate.phase_no
                ),

                damage=(
                    candidate.damage
                ),
            )

            assignments.append(
                assignment
            )

        # --------------------------------
        # Bossごとにまとめる
        # --------------------------------

        assignment_by_record_id = {
            assignment.damage_record_id:
                assignment
            for assignment in assignments
        }

        boss_summaries: list[
            BossAssignmentSummary
        ] = []

        for boss_plan in (
            result.boss_plans
        ):
            boss_assignments = []

            for candidate in (
                boss_plan.selected_candidates
            ):
                assignment = (
                    assignment_by_record_id.get(
                        candidate.damage_record_id
                    )
                )

                if assignment is not None:
                    boss_assignments.append(
                        assignment
                    )

            # 誰も割り当てられていないBossは
            # 表示対象から外す。
            if not boss_assignments:
                continue

            boss_name = (
                boss_name_by_id.get(
                    boss_plan.boss_id,
                    f"Boss {boss_plan.boss_id}",
                )
            )

            boss_summaries.append(
                BossAssignmentSummary(
                    boss_id=(
                        boss_plan.boss_id
                    ),

                    boss_name=(
                        boss_name
                    ),

                    boss_phase_id=(
                        boss_plan.boss_phase_id
                    ),

                    phase_no=(
                        boss_plan.phase_no
                    ),

                    max_hp=(
                        boss_plan.max_hp
                    ),

                    assignments=tuple(
                        boss_assignments
                    ),

                    assigned_damage=(
                        boss_plan.nominal_damage
                    ),

                    effective_damage=(
                        boss_plan.effective_damage
                    ),

                    overkill_damage=(
                        boss_plan.overkill_damage
                    ),
                )
            )

        # Boss → Player → Team の順。
        #
        # これは表示を安定させるためだけで、
        # 攻撃順序を意味しない。
        assignments.sort(
            key=lambda assignment: (
                assignment.boss_id,
                assignment.phase_no,
                assignment.player_name.casefold(),
                assignment.team_no,
            )
        )

        boss_summaries.sort(
            key=lambda summary: (
                summary.boss_id,
                summary.phase_no,
            )
        )

        return UnionAssignmentPlan(
            raid_id=raid_id,

            assignments=tuple(
                assignments
            ),

            boss_summaries=tuple(
                boss_summaries
            ),

            attack_count=(
                result.attack_count
            ),

            total_nominal_damage=(
                result.total_nominal_damage
            ),

            total_effective_damage=(
                result.total_effective_damage
            ),
        )