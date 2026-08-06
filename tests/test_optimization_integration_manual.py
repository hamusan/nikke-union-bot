from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select

from bot.core.database import session_scope
from bot.data import get_boss_phase_hp
from bot.models import Boss, Raid
from bot.services.optimization.assignment_service import (
    UnionAssignmentService,
)
from bot.services.optimization.candidate_service import (
    OptimizationCandidateService,
)


MAX_ATTACKS_PER_PLAYER = 3


def get_active_raid() -> tuple[int, str]:
    """現在のActive Raidを取得する。"""

    with session_scope() as session:
        raid = session.scalar(
            select(Raid)
            .where(
                Raid.active.is_(True)
            )
            .order_by(
                Raid.id.desc()
            )
        )

        if raid is None:
            raise RuntimeError(
                "Active Raidがありません。"
            )

        return (
            raid.id,
            raid.name,
        )


def main() -> None:
    raid_id, raid_name = (
        get_active_raid()
    )

    print(
        "================================"
    )
    print(
        "Optimization Integration Test"
    )
    print(
        "================================"
    )

    print(
        "Raid ID:",
        raid_id,
    )

    print(
        "Raid:",
        raid_name,
    )

    print()

    # ====================================================
    # Candidate生成
    # ====================================================

    candidate_service = (
        OptimizationCandidateService()
    )

    candidates = (
        candidate_service.build_for_raid(
            raid_id
        )
    )

    print(
        "Candidates:",
        len(candidates),
    )

    candidate_players = {
        candidate.player_id
        for candidate in candidates
    }

    candidate_teams = {
        candidate.team_id
        for candidate in candidates
    }

    candidate_bosses = {
        candidate.boss_id
        for candidate in candidates
    }

    candidate_phases = {
        (
            candidate.boss_id,
            candidate.phase_no,
        )
        for candidate in candidates
    }

    print(
        "Candidate Players:",
        len(candidate_players),
    )

    print(
        "Candidate Teams:",
        len(candidate_teams),
    )

    print(
        "Candidate Bosses:",
        len(candidate_bosses),
    )

    print(
        "Candidate Boss Phases:",
        len(candidate_phases),
    )

    print()

    # ====================================================
    # Candidate自体の整合性
    # ====================================================

    for candidate in candidates:
        assert len(
            candidate.character_ids
        ) == 5, (
            "5人編成ではないCandidateがあります: "
            f"damage_record_id="
            f"{candidate.damage_record_id}"
        )

        assert len(
            set(candidate.character_ids)
        ) == 5, (
            "同一キャラが重複したCandidateがあります: "
            f"damage_record_id="
            f"{candidate.damage_record_id}"
        )

        assert candidate.damage > 0, (
            "damage <= 0 のCandidateがあります: "
            f"damage_record_id="
            f"{candidate.damage_record_id}"
        )

    print(
        "[OK] Candidate validation"
    )

    # ====================================================
    # OR-Tools実行
    # ====================================================

    assignment_service = (
        UnionAssignmentService()
    )

    plan = assignment_service.build_for_raid(
        raid_id=raid_id,
        max_attacks_per_player=(
            MAX_ATTACKS_PER_PLAYER
        ),
    )

    print()
    print(
        "Selected attacks:",
        plan.attack_count,
    )

    print(
        "Total nominal damage:",
        f"{plan.total_nominal_damage:,}",
    )

    print(
        "Total effective damage:",
        f"{plan.total_effective_damage:,}",
    )

    print()

    # ====================================================
    # Plan基本整合性
    # ====================================================

    assert plan.raid_id == raid_id

    assert (
        plan.attack_count
        == len(plan.assignments)
    ), (
        "attack_countとassignments数が"
        "一致しません。"
    )

    calculated_nominal = sum(
        assignment.damage
        for assignment
        in plan.assignments
    )

    assert (
        calculated_nominal
        == plan.total_nominal_damage
    ), (
        "total_nominal_damageが"
        "assignments合計と一致しません。"
    )

    print(
        "[OK] Plan totals"
    )

    # ====================================================
    # 同じDamageRecordが複数選ばれていない
    # ====================================================

    selected_record_ids = [
        assignment.damage_record_id
        for assignment
        in plan.assignments
    ]

    assert (
        len(selected_record_ids)
        == len(
            set(selected_record_ids)
        )
    ), (
        "同じDamageRecordが"
        "複数回選択されています。"
    )

    candidate_record_ids = {
        candidate.damage_record_id
        for candidate in candidates
    }

    for record_id in selected_record_ids:
        assert (
            record_id
            in candidate_record_ids
        ), (
            "Candidateに存在しないDamageRecordが"
            "選択されています: "
            f"{record_id}"
        )

    print(
        "[OK] DamageRecord uniqueness"
    )

    # ====================================================
    # 1 Player 最大3凸
    # ====================================================

    attacks_by_player: dict[
        int,
        list,
    ] = defaultdict(list)

    for assignment in plan.assignments:
        attacks_by_player[
            assignment.player_id
        ].append(
            assignment
        )

    for (
        player_id,
        assignments,
    ) in attacks_by_player.items():
        assert (
            len(assignments)
            <= MAX_ATTACKS_PER_PLAYER
        ), (
            "Playerの最大凸数を超えています: "
            f"player_id={player_id}, "
            f"count={len(assignments)}"
        )

    print(
        "[OK] Maximum 3 attacks per player"
    )

    # ====================================================
    # 同じPlayerが同じTeamを2回使っていない
    # ====================================================

    for (
        player_id,
        assignments,
    ) in attacks_by_player.items():
        team_ids = [
            assignment.team_id
            for assignment
            in assignments
        ]

        assert (
            len(team_ids)
            == len(set(team_ids))
        ), (
            "同じPlayerが同じTeamを"
            "複数回使用しています: "
            f"player_id={player_id}"
        )

    print(
        "[OK] Team uniqueness per player"
    )

    # ====================================================
    # 同じPlayer内でCharacter重複禁止
    # ====================================================

    for (
        player_id,
        assignments,
    ) in attacks_by_player.items():
        used_characters: set[str] = set()

        for assignment in assignments:
            character_names = set(
                assignment.character_names
            )

            assert (
                len(character_names) == 5
            ), (
                "表示用Character情報が5人ではありません: "
                f"player_id={player_id}, "
                f"team_id={assignment.team_id}"
            )

            overlap = (
                used_characters
                & character_names
            )

            assert not overlap, (
                "同じPlayerの複数凸で"
                "Characterが重複しています: "
                f"player_id={player_id}, "
                f"characters="
                f"{sorted(overlap)}"
            )

            used_characters.update(
                character_names
            )

    print(
        "[OK] Character overlap constraint"
    )

    # ====================================================
    # BossMaster HP検証
    # ====================================================

    boss_ids = {
        summary.boss_id
        for summary
        in plan.boss_summaries
    }

    boss_key_by_id: dict[
        int,
        str | None,
    ] = {}

    if boss_ids:
        with session_scope() as session:
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

            boss_key_by_id = {
                boss.id: boss.boss_key
                for boss in bosses
            }

    for summary in plan.boss_summaries:
        boss_key = (
            boss_key_by_id.get(
                summary.boss_id
            )
        )

        assert boss_key is not None, (
            "最適化結果にBoss Master未登録Bossが"
            "含まれています: "
            f"boss_id={summary.boss_id}"
        )

        master_hp = get_boss_phase_hp(
            boss_key=boss_key,
            phase_no=summary.phase_no,
        )

        assert master_hp is not None, (
            "Boss MasterにPhase HPがありません: "
            f"boss_key={boss_key}, "
            f"phase={summary.phase_no}"
        )

        assert (
            summary.max_hp
            == master_hp
        ), (
            "最適化で使用されたHPが"
            "Boss Masterと一致しません: "
            f"boss_key={boss_key}, "
            f"phase={summary.phase_no}, "
            f"plan={summary.max_hp}, "
            f"master={master_hp}"
        )

    print(
        "[OK] Boss Master HP"
    )

    # ====================================================
    # BossごとのDamage計算
    # ====================================================

    calculated_total_effective = 0

    for summary in plan.boss_summaries:
        calculated_assigned = sum(
            assignment.damage
            for assignment
            in summary.assignments
        )

        assert (
            calculated_assigned
            == summary.assigned_damage
        ), (
            "Boss assigned_damageが"
            "assignments合計と一致しません: "
            f"boss_id={summary.boss_id}"
        )

        expected_effective = min(
            calculated_assigned,
            summary.max_hp,
        )

        expected_overkill = max(
            0,
            calculated_assigned
            - summary.max_hp,
        )

        assert (
            summary.effective_damage
            == expected_effective
        ), (
            "effective_damageが不正です: "
            f"boss_id={summary.boss_id}"
        )

        assert (
            summary.overkill_damage
            == expected_overkill
        ), (
            "overkill_damageが不正です: "
            f"boss_id={summary.boss_id}"
        )

        calculated_total_effective += (
            summary.effective_damage
        )

    assert (
        calculated_total_effective
        == plan.total_effective_damage
    ), (
        "total_effective_damageが"
        "Bossごとの合計と一致しません。"
    )

    print(
        "[OK] Effective damage / Overkill"
    )

    # ====================================================
    # 結果表示
    # ====================================================

    print()
    print(
        "--------------------------------"
    )
    print(
        "Selected Assignments"
    )
    print(
        "--------------------------------"
    )

    if not plan.assignments:
        print(
            "割り当てなし"
        )

    for assignment in plan.assignments:
        print(
            (
                f"Player {assignment.player_name}"
                f" | Team #{assignment.team_no}"
                f" | {assignment.boss_name}"
                f" Phase {assignment.phase_no}"
                f" | {assignment.damage:,}"
            )
        )

        print(
            "  Characters:",
            " / ".join(
                assignment.character_names
            ),
        )

    # ====================================================
    # Coverage
    # ====================================================

    print()
    print(
        "--------------------------------"
    )
    print(
        "Test Coverage"
    )
    print(
        "--------------------------------"
    )

    if len(candidate_players) < 2:
        print(
            "[WARN] Playerが1人以下です。"
            "複数Player競合はまだ未検証です。"
        )
    else:
        print(
            "[OK] Multiple players"
        )

    if len(candidate_teams) < 3:
        print(
            "[WARN] Team候補が3個未満です。"
            "3凸選択の十分な競合は"
            "まだ未検証の可能性があります。"
        )
    else:
        print(
            "[OK] Multiple teams"
        )

    if len(candidate_bosses) < 2:
        print(
            "[WARN] Boss候補が1体以下です。"
            "複数Boss間の最適配分は"
            "まだ未検証です。"
        )
    else:
        print(
            "[OK] Multiple bosses"
        )

    print()
    print(
        "================================"
    )
    print(
        "Optimization Integration TEST OK"
    )
    print(
        "================================"
    )


if __name__ == "__main__":
    main()