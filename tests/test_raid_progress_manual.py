from bot.services.raid_progress import (
    FINAL_REACHED_PHASE,
    RaidProgressState,
    is_final_reached,
    next_phase,
)


def main() -> None:
    # --------------------------------
    # Phase遷移
    # --------------------------------

    assert next_phase(1) == 2
    assert next_phase(2) == 3
    assert next_phase(3) == 4

    # 最終到達後はそれ以上進まない
    assert next_phase(4) == 4

    print(
        "[OK] Phase transition:"
        " 1 -> 2 -> 3 -> final"
    )

    # --------------------------------
    # Final判定
    # --------------------------------

    assert not is_final_reached(1)
    assert not is_final_reached(2)
    assert not is_final_reached(3)

    assert is_final_reached(
        FINAL_REACHED_PHASE
    )

    print(
        "[OK] Final reached detection"
    )

    # --------------------------------
    # State
    # --------------------------------

    phase3 = RaidProgressState(
        raid_id=1,
        raid_name="Test Raid",
        current_phase=3,
    )

    assert (
        phase3.phase_label
        == "Phase 3"
    )

    assert (
        phase3.optimization_available
        is True
    )

    assert (
        phase3.final_reached
        is False
    )

    final = RaidProgressState(
        raid_id=1,
        raid_name="Test Raid",
        current_phase=4,
    )

    assert (
        final.phase_label
        == "最終フェーズ到達済み"
    )

    assert (
        final.optimization_available
        is False
    )

    assert (
        final.final_reached
        is True
    )

    print(
        "[OK] RaidProgressState"
    )

    # --------------------------------
    # 不正値
    # --------------------------------

    try:
        next_phase(5)

    except ValueError:
        print(
            "[OK] Invalid phase rejected"
        )

    else:
        raise AssertionError(
            "Phase 5が拒否されませんでした。"
        )

    print()
    print(
        "Raid Progress TEST OK"
    )


if __name__ == "__main__":
    main()