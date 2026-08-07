from bot.services.optimization.context import (
    OptimizationBossTarget,
    OptimizationRaidContext,
)


def main() -> None:
    bosses = (
        OptimizationBossTarget(
            boss_id=1,
            boss_no=1,
            boss_name="Boss 1",
            boss_phase_id=101,
            phase_no=2,
            max_hp=1000,
            remaining_hp=300,
        ),

        OptimizationBossTarget(
            boss_id=2,
            boss_no=2,
            boss_name="Boss 2",
            boss_phase_id=102,
            phase_no=2,
            max_hp=2000,
            remaining_hp=0,
        ),

        OptimizationBossTarget(
            boss_id=3,
            boss_no=3,
            boss_name="Boss 3",
            boss_phase_id=103,
            phase_no=2,
            max_hp=3000,
            remaining_hp=1500,
        ),
    )

    context = OptimizationRaidContext(
        raid_id=1,
        raid_name="Test Raid",
        phase_no=2,
        final_reached=False,
        bosses=bosses,
    )

    # 撃破済みBossは除外
    assert len(context.active_bosses) == 2

    assert (
        context.active_boss_phase_ids
        == frozenset({
            101,
            103,
        })
    )

    print(
        "[OK] Defeated Boss excluded"
    )

    # Solverには最大HPではなく残HPを渡す
    assert (
        context.boss_hp_by_phase_id
        == {
            101: 300,
            103: 1500,
        }
    )

    print(
        "[OK] Remaining HP used"
    )

    # Phase 3攻略完了後
    final = OptimizationRaidContext(
        raid_id=1,
        raid_name="Test Raid",
        phase_no=4,
        final_reached=True,
        bosses=(),
    )

    assert final.final_reached

    assert (
        final.boss_hp_by_phase_id
        == {}
    )

    print(
        "[OK] Final reached context"
    )

    print()
    print(
        "Optimization Context TEST OK"
    )


if __name__ == "__main__":
    main()