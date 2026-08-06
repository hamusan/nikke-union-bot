from bot.core.database import session_scope
from bot.repositories.damage_repository import (
    DamageRepository,
)
from bot.services.optimization.candidate import (
    OptimizationCandidate,
)


class OptimizationCandidateService:
    """最適化用候補データを生成するService。"""

    def build_for_raid(
        self,
        raid_id: int,
    ) -> list[OptimizationCandidate]:
        """
        RaidのDamageRecordを、
        OR-Tools用データへ変換する。
        """

        with session_scope() as session:
            repository = DamageRepository(
                session
            )

            records = repository.list_by_raid_id(
                raid_id
            )

            candidates: list[
                OptimizationCandidate
            ] = []

            for record in records:
                team = record.team
                phase = record.boss_phase

                if team is None:
                    continue

                if phase is None:
                    continue

                # 非アクティブTeamは最適化から除外。
                if not team.active:
                    continue

                members = list(
                    team.members
                )

                # 5人揃っていないTeamは
                # 最適化対象にしない。
                if len(members) != 5:
                    continue

                character_ids = tuple(
                    sorted(
                        member.character_id
                        for member in members
                    )
                )

                # 同じCharacterが重複していたら
                # 不正Teamなので除外。
                if (
                    len(set(character_ids))
                    != 5
                ):
                    continue

                candidate = (
                    OptimizationCandidate(
                        damage_record_id=record.id,

                        player_id=team.player_id,

                        team_id=team.id,
                        team_no=team.team_no,

                        boss_id=record.boss_id,
                        boss_phase_id=phase.id,
                        phase_no=phase.phase_no,

                        damage=record.damage,

                        character_ids=character_ids,
                    )
                )

                candidates.append(
                    candidate
                )

            return candidates