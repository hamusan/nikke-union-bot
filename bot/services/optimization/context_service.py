from __future__ import annotations

from bot.services.optimization.context import (
    OptimizationBossTarget,
    OptimizationRaidContext,
)
from bot.services.raid_boss_progress_service import (
    RaidBossProgressService,
)
from bot.services.raid_progress_service import (
    RaidProgressService,
)


class OptimizationRaidContextService:
    """
    最適化に必要なRaid進行状態を
    まとめて取得するService。
    """

    def __init__(
        self,
    ) -> None:
        self._raid_service = (
            RaidProgressService()
        )

        self._boss_progress_service = (
            RaidBossProgressService()
        )

    def build_for_raid(
        self,
        raid_id: int,
    ) -> OptimizationRaidContext:
        """
        現在PhaseとBoss残HPから
        最適化Contextを生成する。
        """

        raid = (
            self._raid_service
            .get_by_id(
                raid_id
            )
        )

        if raid is None:
            raise ValueError(
                (
                    "Raidが存在しません: "
                    f"raid_id={raid_id}"
                )
            )

        # --------------------------------
        # Phase 3攻略済み
        # --------------------------------

        if raid.final_reached:
            return OptimizationRaidContext(
                raid_id=raid.raid_id,
                raid_name=raid.raid_name,
                phase_no=raid.current_phase,
                final_reached=True,
                bosses=(),
            )

        # --------------------------------
        # 現在PhaseのBoss状態
        # --------------------------------

        phase = (
            self._boss_progress_service
            .get_phase(
                raid_id=raid.raid_id,
                phase_no=(
                    raid.current_phase
                ),
            )
        )

        # --------------------------------
        # Boss 5体分のHPが無ければ
        # 最適化しない
        # --------------------------------

        if not phase.all_bosses_configured:
            missing = ", ".join(
                f"#{boss_no}"
                for boss_no
                in phase.missing_boss_nos
            )

            raise ValueError(
                (
                    f"Phase {raid.current_phase} の"
                    "Boss HPデータが不足しています。"
                    f" 未設定: {missing}"
                )
            )

        bosses = tuple(
            OptimizationBossTarget(
                boss_id=boss.boss_id,
                boss_no=boss.boss_no,
                boss_name=boss.boss_name,

                boss_phase_id=(
                    boss.boss_phase_id
                ),

                phase_no=boss.phase_no,

                max_hp=boss.max_hp,

                remaining_hp=(
                    boss.remaining_hp
                ),
            )

            for boss in phase.bosses
        )

        return OptimizationRaidContext(
            raid_id=raid.raid_id,
            raid_name=raid.raid_name,

            phase_no=raid.current_phase,

            final_reached=False,

            bosses=bosses,
        )