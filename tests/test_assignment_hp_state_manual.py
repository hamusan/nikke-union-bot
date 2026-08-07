from bot.services.optimization.assignment import (
    BossAssignmentSummary,
)


def main() -> None:
    summary = BossAssignmentSummary(
        boss_id=1,
        boss_name="Test Boss",

        boss_phase_id=101,
        phase_no=2,

        max_hp=1000,
        remaining_hp=300,

        assignments=(),

        assigned_damage=400,
        effective_damage=300,
        overkill_damage=100,
    )

    assert summary.max_hp == 1000
    assert summary.remaining_hp == 300

    assert summary.damage_taken == 700
    assert summary.defeated is False

    print(
        "[OK] Max HP / Remaining HP separated"
    )

    defeated = BossAssignmentSummary(
        boss_id=1,
        boss_name="Test Boss",

        boss_phase_id=101,
        phase_no=2,

        max_hp=1000,
        remaining_hp=0,

        assignments=(),

        assigned_damage=1000,
        effective_damage=1000,
        overkill_damage=0,
    )

    assert defeated.defeated is True

    print(
        "[OK] Defeated state"
    )

    print()
    print(
        "Assignment HP State TEST OK"
    )


if __name__ == "__main__":
    main()