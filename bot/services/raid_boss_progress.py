from __future__ import annotations

from dataclasses import dataclass


BOSS_SLOTS = (
    1,
    2,
    3,
    4,
    5,
)


@dataclass(
    frozen=True
)
class BossProgressState:
    """Boss 1体のPhase進行状態。"""

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
        return (
            self.remaining_hp <= 0
        )

    @property
    def damage_taken(
        self,
    ) -> int:
        return max(
            0,
            self.max_hp
            - self.remaining_hp,
        )

    @property
    def remaining_ratio(
        self,
    ) -> float:
        if self.max_hp <= 0:
            return 0.0

        return (
            self.remaining_hp
            / self.max_hp
        )


@dataclass(
    frozen=True
)
class RaidPhaseProgressState:
    """Raidの1Phase全体の進行状態。"""

    raid_id: int
    raid_name: str

    phase_no: int

    bosses: tuple[
        BossProgressState,
        ...
    ]

    missing_boss_nos: tuple[
        int,
        ...
    ]

    @property
    def all_bosses_configured(
        self,
    ) -> bool:
        return (
            len(self.bosses) == 5
            and not self.missing_boss_nos
        )

    @property
    def all_defeated(
        self,
    ) -> bool:
        if not self.all_bosses_configured:
            return False

        return all(
            boss.defeated
            for boss in self.bosses
        )

    @property
    def defeated_count(
        self,
    ) -> int:
        return sum(
            1
            for boss in self.bosses
            if boss.defeated
        )

    @property
    def total_remaining_hp(
        self,
    ) -> int:
        return sum(
            boss.remaining_hp
            for boss in self.bosses
        )


def calculate_remaining_hp(
    current_hp: int,
    damage: int,
) -> int:
    """
    Damage適用後の残HPを計算する。

    0未満にはならない。
    """

    if current_hp < 0:
        raise ValueError(
            (
                "current_hpは0以上で"
                "ある必要があります。"
            )
        )

    if damage < 0:
        raise ValueError(
            (
                "damageは0以上で"
                "ある必要があります。"
            )
        )

    return max(
        0,
        current_hp - damage,
    )