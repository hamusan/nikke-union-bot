from pathlib import Path

from bot.services.optimization.assignment import (
    AttackAssignment,
    BossAssignmentSummary,
    UnionAssignmentPlan,
)
from bot.services.optimization.plan_renderer import (
    OptimizationPlanImageRenderer,
)


def main() -> None:
    # ================================================
    # Boss #1
    # ================================================

    attack_1 = AttackAssignment(
        damage_record_id=1,
        player_id=1,
        player_name="Player A",
        team_id=1,
        team_no=1,
        character_names=(
            "クラウン",
            "リター",
            "レッドフード",
            "アリス",
            "ナガ",
        ),
        boss_id=1,
        boss_name="グレイブディガー",
        boss_phase_id=101,
        phase_no=3,
        damage=20_000_000_000,
    )

    attack_2 = AttackAssignment(
        damage_record_id=2,
        player_id=2,
        player_name="Player B",
        team_id=2,
        team_no=2,
        character_names=(
            "ティア",
            "ナガ",
            "モダニア",
            "黒紅蓮",
            "ラプンツェル",
        ),
        boss_id=1,
        boss_name="グレイブディガー",
        boss_phase_id=101,
        phase_no=3,
        damage=15_000_000_000,
    )

    boss_1 = BossAssignmentSummary(
        boss_id=1,
        boss_name="グレイブディガー",
        boss_phase_id=101,
        phase_no=3,

        max_hp=150_841_811_600,
        remaining_hp=30_000_000_000,

        assignments=(
            attack_1,
            attack_2,
        ),

        assigned_damage=35_000_000_000,
        effective_damage=30_000_000_000,
        overkill_damage=5_000_000_000,
    )

    # ================================================
    # Boss #2
    # ================================================

    attack_3 = AttackAssignment(
        damage_record_id=3,
        player_id=3,
        player_name="Player C",
        team_id=3,
        team_no=1,
        character_names=(
            "シンデレラ",
            "ルージュ",
            "マスト",
            "プリバティ",
            "ヘルム",
        ),
        boss_id=2,
        boss_name="Test Boss 2",
        boss_phase_id=102,
        phase_no=3,
        damage=18_000_000_000,
    )

    boss_2 = BossAssignmentSummary(
        boss_id=2,
        boss_name="Test Boss 2",
        boss_phase_id=102,
        phase_no=3,

        max_hp=80_000_000_000,
        remaining_hp=60_000_000_000,

        assignments=(
            attack_3,
        ),

        assigned_damage=18_000_000_000,
        effective_damage=18_000_000_000,
        overkill_damage=0,
    )

    # ================================================
    # Plan
    # ================================================

    plan = UnionAssignmentPlan(
        raid_id=1,

        assignments=(
            attack_1,
            attack_2,
            attack_3,
        ),

        boss_summaries=(
            boss_1,
            boss_2,
        ),

        attack_count=3,

        total_nominal_damage=(
            53_000_000_000
        ),

        total_effective_damage=(
            48_000_000_000
        ),
    )

    renderer = (
        OptimizationPlanImageRenderer()
    )

    boss_images = (
        renderer.render_boss_images(
            plan
        )
    )

    assert len(boss_images) == 2

    output_dir = Path(
        "uploads/optimization_test"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for rendered in boss_images:
        output_path = (
            output_dir
            / rendered.filename
        )

        output_path.write_bytes(
            rendered.png_bytes
        )

        assert (
            output_path.exists()
        )

        assert (
            output_path.stat().st_size
            > 0
        )

        print(
            "[OK]",
            rendered.boss_name,
            "->",
            output_path,
        )

    print()
    print(
        "Boss Image Renderer TEST OK"
    )


if __name__ == "__main__":
    main()