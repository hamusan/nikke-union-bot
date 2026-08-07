from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OptimizationBossTarget:
    """
    現在の最適化対象となるBoss状態。
    """

    boss_id: int
    boss_no: int
    boss_name: str

    boss_phase_id: int
    phase_no: int

    max_hp: int
    remaining_hp: int

    @property
    def defeated(
        self,
    ) -> bool:
        return self.remaining_hp <= 0


@dataclass(frozen=True)
class OptimizationRaidContext:
    """
    1回の最適化で使用する
    Raid進行状況。
    """

    raid_id: int
    raid_name: str

    phase_no: int
    final_reached: bool

    bosses: tuple[
        OptimizationBossTarget,
        ...
    ]

    @property
    def active_bosses(
        self,
    ) -> tuple[
        OptimizationBossTarget,
        ...
    ]:
        """
        HPが残っているBossだけ返す。
        """

        return tuple(
            boss
            for boss in self.bosses
            if not boss.defeated
        )

    @property
    def boss_hp_by_phase_id(
        self,
    ) -> dict[int, int]:
        """
        Solverへ渡すHP上限。

        最大HPではなく、
        「現在の残HP」を渡す。
        """

        return {
            boss.boss_phase_id:
                boss.remaining_hp

            for boss in self.active_bosses
        }

    @property
    def active_boss_phase_ids(
        self,
    ) -> frozenset[int]:
        return frozenset(
            boss.boss_phase_id
            for boss in self.active_bosses
        )