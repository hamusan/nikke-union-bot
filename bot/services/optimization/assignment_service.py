from collections import defaultdict

from sqlalchemy import select

from bot.core.database import session_scope
from bot.models import (
    Boss,
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

from bot.services.optimization.context_service import (
    OptimizationRaidContextService,
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

        self._context_service = (
            OptimizationRaidContextService()
        )

        self._solver = (
            UnionOptimizationSolver()
        )

    def build_for_raid(
        self,
        raid_id: int,
        max_attacks_per_player: int = 3,
    ) -> UnionAssignmentPlan:
        """
        現在のRaid進行状況を考慮して
        最適攻撃割り当てを生成する。
        """

        # ====================================
        # 現在のRaid最適化Context
        # ====================================

        context = (
            self._context_service
            .build_for_raid(
                raid_id
            )
        )

        # ====================================
        # Phase 3攻略済み
        # ====================================

        if context.final_reached:
            return UnionAssignmentPlan(
                raid_id=raid_id,
                assignments=(),
                boss_summaries=(),
                attack_count=0,
                total_nominal_damage=0,
                total_effective_damage=0,
            )

        # ====================================
        # 全Damage候補
        # ====================================

        all_candidates = (
            self._candidate_service
            .build_for_raid(
                raid_id=raid_id
            )
        )

        active_phase_ids = (
            context.active_boss_phase_ids
        )

        # ====================================
        # 現在Phase
        # +
        # HPが残っているBoss
        # だけに限定
        # ====================================

        candidates = [
            candidate
            for candidate
            in all_candidates

            if (
                candidate.phase_no
                == context.phase_no

                and candidate.boss_phase_id
                in active_phase_ids
            )
        ]

        if not candidates:
            return UnionAssignmentPlan(
                raid_id=raid_id,
                assignments=(),
                boss_summaries=(),
                attack_count=0,
                total_nominal_damage=0,
                total_effective_damage=0,
            )

        # ====================================
        # Solverへ渡すHP
        #
        # BossPhase.max_hpではなく
        # 現在のremaining_hp
        # ====================================

        boss_hp_by_phase_id = (
            context.boss_hp_by_phase_id
        )

        # ====================================
        # OR-Tools
        # ====================================

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

        boss_target_by_phase_id = {
            boss.boss_phase_id: boss
            for boss in context.bosses
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

            target = (
                boss_target_by_phase_id.get(
                    boss_plan.boss_phase_id
                )
            )

            if target is None:
                raise ValueError(
                    (
                        "最適化対象Bossの"
                        "Raid Contextがありません: "
                        "boss_phase_id="
                        f"{boss_plan.boss_phase_id}"
                    )
                )
            
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
                    
                    remaining_hp=(
                        target.remaining_hp
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