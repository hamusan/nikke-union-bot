from bot.services.raid_progress import (
    decide_phase_transition,
)


def main() -> None:
    # ====================================
    # Boss設定不足
    # ====================================

    result = decide_phase_transition(
        current_phase=1,
        all_bosses_configured=False,
        all_bosses_defeated=False,
    )

    assert (
        result.should_advance
        is False
    )

    assert (
        result.reason
        == "boss_config_incomplete"
    )

    print(
        "[OK] Incomplete Boss config"
    )

    # ====================================
    # Bossは5体いるが生存中
    # ====================================

    result = decide_phase_transition(
        current_phase=1,
        all_bosses_configured=True,
        all_bosses_defeated=False,
    )

    assert (
        result.should_advance
        is False
    )

    assert (
        result.reason
        == "bosses_remaining"
    )

    print(
        "[OK] Bosses remaining"
    )

    # ====================================
    # Phase 1 全撃破
    # ====================================

    result = decide_phase_transition(
        current_phase=1,
        all_bosses_configured=True,
        all_bosses_defeated=True,
    )

    assert result.should_advance

    assert (
        result.reason
        == "phase_complete"
    )

    print(
        "[OK] Phase 1 complete"
    )

    # ====================================
    # Phase 2 全撃破
    # ====================================

    result = decide_phase_transition(
        current_phase=2,
        all_bosses_configured=True,
        all_bosses_defeated=True,
    )

    assert result.should_advance

    print(
        "[OK] Phase 2 complete"
    )

    # ====================================
    # Phase 3 全撃破
    # ====================================

    result = decide_phase_transition(
        current_phase=3,
        all_bosses_configured=True,
        all_bosses_defeated=True,
    )

    assert result.should_advance

    print(
        "[OK] Phase 3 complete"
    )

    # ====================================
    # 最終フェーズ到達後
    # ====================================

    result = decide_phase_transition(
        current_phase=4,
        all_bosses_configured=True,
        all_bosses_defeated=True,
    )

    assert (
        result.should_advance
        is False
    )

    assert (
        result.reason
        == "final_reached"
    )

    print(
        "[OK] Final phase does not advance"
    )

    print()
    print(
        "Raid Phase Transition TEST OK"
    )


if __name__ == "__main__":
    main()