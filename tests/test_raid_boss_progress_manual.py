from bot.services.raid_boss_progress import (
    BossProgressState,
    RaidPhaseProgressState,
    calculate_remaining_hp,
)


def main() -> None:
    # --------------------------------
    # Damage計算
    # --------------------------------

    assert (
        calculate_remaining_hp(
            1000,
            300,
        )
        == 700
    )

    assert (
        calculate_remaining_hp(
            1000,
            1000,
        )
        == 0
    )

    assert (
        calculate_remaining_hp(
            1000,
            1500,
        )
        == 0
    )

    print(
        "[OK] Remaining HP calculation"
    )

    # --------------------------------
    # Boss状態
    # --------------------------------

    boss1 = BossProgressState(
        boss_id=1,
        boss_no=1,
        boss_name="Boss A",
        boss_phase_id=101,
        phase_no=1,
        max_hp=1000,
        remaining_hp=0,
    )

    boss2 = BossProgressState(
        boss_id=2,
        boss_no=2,
        boss_name="Boss B",
        boss_phase_id=102,
        phase_no=1,
        max_hp=2000,
        remaining_hp=500,
    )

    assert boss1.defeated
    assert not boss2.defeated

    assert (
        boss1.damage_taken
        == 1000
    )

    assert (
        boss2.damage_taken
        == 1500
    )

    print(
        "[OK] Boss state"
    )

    # --------------------------------
    # 不完全なPhase
    # --------------------------------

    incomplete = (
        RaidPhaseProgressState(
            raid_id=1,
            raid_name="Test",
            phase_no=1,
            bosses=(
                boss1,
                boss2,
            ),
            missing_boss_nos=(
                3,
                4,
                5,
            ),
        )
    )

    assert not (
        incomplete
        .all_bosses_configured
    )

    assert not incomplete.all_defeated

    print(
        "[OK] Missing Boss detection"
    )

    # --------------------------------
    # 5体全撃破
    # --------------------------------

    bosses = tuple(
        BossProgressState(
            boss_id=i,
            boss_no=i,
            boss_name=f"Boss {i}",
            boss_phase_id=100 + i,
            phase_no=1,
            max_hp=1000,
            remaining_hp=0,
        )
        for i in range(
            1,
            6,
        )
    )

    complete = (
        RaidPhaseProgressState(
            raid_id=1,
            raid_name="Test",
            phase_no=1,
            bosses=bosses,
            missing_boss_nos=(),
        )
    )

    assert (
        complete
        .all_bosses_configured
    )

    assert complete.all_defeated

    assert (
        complete.defeated_count
        == 5
    )

    assert (
        complete.total_remaining_hp
        == 0
    )

    print(
        "[OK] All 5 Bosses defeated"
    )

    print()
    print(
        "Raid Boss Progress TEST OK"
    )


if __name__ == "__main__":
    main()