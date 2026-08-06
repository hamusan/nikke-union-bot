from pathlib import Path

from bot.services.optimization.assignment import (
    AttackAssignment,
    BossAssignmentSummary,
    UnionAssignmentPlan,
)
from bot.services.optimization.plan_renderer import (
    OptimizationPlanImageRenderer,
)


OUTPUT_PATH = Path(
    "uploads/optimization/"
    "optimization_plan_preview.png"
)


def main() -> None:
    attack_1 = AttackAssignment(
        damage_record_id=1,

        player_id=1,
        player_name="Player A",

        team_id=1,
        team_no=1,

        character_names=(
            "シンデレラ",
            "レッドフード",
            "ヘルム",
            "ベスティー",
            "ベスティー：タクティカル・アップ",
        ),

        boss_id=1,
        boss_name="グレイブディガー",

        boss_phase_id=1,
        phase_no=3,

        damage=80_000_000_000,
    )

    attack_2 = AttackAssignment(
        damage_record_id=2,

        player_id=2,
        player_name="Player B",

        team_id=2,
        team_no=3,

        character_names=(
            "キャラクターA",
            "キャラクターB",
            "キャラクターC",
            "キャラクターD",
            "キャラクターE",
        ),

        boss_id=1,
        boss_name="グレイブディガー",

        boss_phase_id=1,
        phase_no=3,

        damage=90_000_000_000,
    )

    assigned_damage = (
        attack_1.damage
        + attack_2.damage
    )

    max_hp = 150_841_811_600

    effective_damage = min(
        assigned_damage,
        max_hp,
    )

    boss_summary = BossAssignmentSummary(
        boss_id=1,
        boss_name="グレイブディガー",

        boss_phase_id=1,
        phase_no=3,

        max_hp=max_hp,

        assignments=(
            attack_1,
            attack_2,
        ),

        assigned_damage=(
            assigned_damage
        ),

        effective_damage=(
            effective_damage
        ),

        overkill_damage=max(
            0,
            assigned_damage - max_hp,
        ),
    )

    plan = UnionAssignmentPlan(
        raid_id=1,

        assignments=(
            attack_1,
            attack_2,
        ),

        boss_summaries=(
            boss_summary,
        ),

        attack_count=2,

        total_nominal_damage=(
            assigned_damage
        ),

        total_effective_damage=(
            effective_damage
        ),
    )

    renderer = (
        OptimizationPlanImageRenderer()
    )

    png = renderer.render(
        plan=plan,
        raid_name="画像テスト用Raid",
    )

    assert png.startswith(
        b"\x89PNG"
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_bytes(
        png
    )

    print(
        "PNG bytes:",
        len(png),
    )

    print(
        "Saved:",
        OUTPUT_PATH,
    )

    print(
        "Optimization Plan Render TEST OK"
    )


if __name__ == "__main__":
    main()