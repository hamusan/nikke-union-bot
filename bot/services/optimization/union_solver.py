from collections import defaultdict
from dataclasses import dataclass

from ortools.sat.python import cp_model

from bot.services.optimization.candidate import (
    OptimizationCandidate,
)


@dataclass(frozen=True)
class BossOptimizationPlan:
    """BossPhaseごとの最適化結果。"""

    boss_id: int
    boss_phase_id: int
    phase_no: int

    max_hp: int

    selected_candidates: tuple[
        OptimizationCandidate,
        ...
    ]

    nominal_damage: int
    effective_damage: int
    overkill_damage: int


@dataclass(frozen=True)
class UnionOptimizationResult:
    """ユニオン全体の最適化結果。"""

    selected_candidates: tuple[
        OptimizationCandidate,
        ...
    ]

    boss_plans: tuple[
        BossOptimizationPlan,
        ...
    ]

    attack_count: int

    total_nominal_damage: int
    total_effective_damage: int


class UnionOptimizationSolver:
    """
    ユニオン全体の攻撃候補を最適化する。

    制約:
    - 1Player最大3凸
    - 同一Player内で同じTeamは1回まで
    - 同一Player内で同じCharacterは1回まで

    目的:
    1. Boss HPを上限とした有効Damageを最大化
    2. 同じ有効Damageなら使用凸数を最小化
    """

    def solve(
        self,
        candidates: list[
            OptimizationCandidate
        ],
        boss_hp_by_phase_id: dict[int, int],
        max_attacks_per_player: int = 3,
    ) -> UnionOptimizationResult:
        """ユニオン全体を最適化する。"""

        if max_attacks_per_player <= 0:
            raise ValueError(
                "max_attacks_per_playerは"
                "1以上である必要があります。"
            )

        if not candidates:
            return UnionOptimizationResult(
                selected_candidates=(),
                boss_plans=(),
                attack_count=0,
                total_nominal_damage=0,
                total_effective_damage=0,
            )

        self._validate_boss_hp(
            candidates=candidates,
            boss_hp_by_phase_id=(
                boss_hp_by_phase_id
            ),
        )

        model = cp_model.CpModel()

        # ------------------------------
        # Candidate選択変数
        # ------------------------------

        variables: dict[
            int,
            cp_model.IntVar,
        ] = {}

        for index, candidate in enumerate(
            candidates
        ):
            variables[index] = (
                model.NewBoolVar(
                    f"candidate_{index}"
                )
            )

        # ------------------------------
        # Playerごとの最大凸数
        # ------------------------------

        player_indexes: dict[
            int,
            list[int],
        ] = defaultdict(list)

        for index, candidate in enumerate(
            candidates
        ):
            player_indexes[
                candidate.player_id
            ].append(
                index
            )

        for indexes in (
            player_indexes.values()
        ):
            model.Add(
                sum(
                    variables[index]
                    for index in indexes
                )
                <= max_attacks_per_player
            )

        # ------------------------------
        # 同じTeamは1回まで
        # ------------------------------

        team_indexes: dict[
            tuple[int, int],
            list[int],
        ] = defaultdict(list)

        for index, candidate in enumerate(
            candidates
        ):
            key = (
                candidate.player_id,
                candidate.team_id,
            )

            team_indexes[
                key
            ].append(
                index
            )

        for indexes in (
            team_indexes.values()
        ):
            model.Add(
                sum(
                    variables[index]
                    for index in indexes
                )
                <= 1
            )

        # ------------------------------
        # 同一Player内で
        # Character再使用禁止
        # ------------------------------

        character_indexes: dict[
            tuple[int, int],
            list[int],
        ] = defaultdict(list)

        for index, candidate in enumerate(
            candidates
        ):
            for character_id in (
                candidate.character_ids
            ):
                key = (
                    candidate.player_id,
                    character_id,
                )

                character_indexes[
                    key
                ].append(
                    index
                )

        for indexes in (
            character_indexes.values()
        ):
            model.Add(
                sum(
                    variables[index]
                    for index in indexes
                )
                <= 1
            )

        # ------------------------------
        # BossPhaseごとのCandidate
        # ------------------------------

        phase_indexes: dict[
            int,
            list[int],
        ] = defaultdict(list)

        for index, candidate in enumerate(
            candidates
        ):
            phase_indexes[
                candidate.boss_phase_id
            ].append(
                index
            )

        # ------------------------------
        # Boss HPを上限にした
        # effective_damageを作る
        # ------------------------------

        effective_variables: dict[
            int,
            cp_model.IntVar,
        ] = {}

        for (
            boss_phase_id,
            indexes,
        ) in phase_indexes.items():
            max_hp = (
                boss_hp_by_phase_id[
                    boss_phase_id
                ]
            )

            effective = model.NewIntVar(
                0,
                max_hp,
                (
                    "effective_damage_"
                    f"{boss_phase_id}"
                ),
            )

            nominal_damage = sum(
                candidates[index].damage
                * variables[index]
                for index in indexes
            )

            # effective_damage <=
            # 選ばれた攻撃の合計Damage
            model.Add(
                effective
                <= nominal_damage
            )

            # effective_damageの上限は
            # NewIntVarでmax_hpに設定済み。
            effective_variables[
                boss_phase_id
            ] = effective

        max_total_effective = sum(
            boss_hp_by_phase_id[
                phase_id
            ]
            for phase_id in (
                effective_variables
            )
        )

        total_effective = model.NewIntVar(
            0,
            max_total_effective,
            "total_effective_damage",
        )

        model.Add(
            total_effective
            == sum(
                effective_variables.values()
            )
        )

        # ==================================================
        # 第1段階
        # 有効Damage最大化
        # ==================================================

        model.Maximize(
            total_effective
        )

        solver = cp_model.CpSolver()

        status = solver.Solve(
            model
        )

        if status not in (
            cp_model.OPTIMAL,
            cp_model.FEASIBLE,
        ):
            return UnionOptimizationResult(
                selected_candidates=(),
                boss_plans=(),
                attack_count=0,
                total_nominal_damage=0,
                total_effective_damage=0,
            )

        best_effective = solver.Value(
            total_effective
        )

        # ==================================================
        # 第2段階
        #
        # 最大Damageを維持したまま、
        # 使用凸数を最小化。
        #
        # HPを十分削れるのに不要な凸まで
        # 選ばれるのを防ぐ。
        # ==================================================

        model.Add(
            total_effective
            == best_effective
        )

        selected_count = model.NewIntVar(
            0,
            len(candidates),
            "selected_attack_count",
        )

        model.Add(
            selected_count
            == sum(
                variables.values()
            )
        )

        model.Minimize(
            selected_count
        )

        solver = cp_model.CpSolver()

        status = solver.Solve(
            model
        )

        if status not in (
            cp_model.OPTIMAL,
            cp_model.FEASIBLE,
        ):
            raise RuntimeError(
                "第2段階の最適化に失敗しました。"
            )

        # ------------------------------
        # 選択Candidateを取得
        # ------------------------------

        selected: list[
            OptimizationCandidate
        ] = []

        for index, candidate in enumerate(
            candidates
        ):
            if (
                solver.Value(
                    variables[index]
                )
                == 1
            ):
                selected.append(
                    candidate
                )

        # Player → Team順で
        # 見やすく並べる。
        selected.sort(
            key=lambda candidate: (
                candidate.player_id,
                candidate.team_no,
                candidate.boss_id,
            )
        )

        # ------------------------------
        # Bossごとの結果
        # ------------------------------

        boss_plans: list[
            BossOptimizationPlan
        ] = []

        for (
            boss_phase_id,
            indexes,
        ) in sorted(
            phase_indexes.items()
        ):
            phase_candidates = [
                candidates[index]
                for index in indexes
                if (
                    solver.Value(
                        variables[index]
                    )
                    == 1
                )
            ]

            if phase_candidates:
                reference = (
                    phase_candidates[0]
                )
            else:
                # Candidate自体は存在するので
                # metadata取得用。
                reference = (
                    candidates[
                        indexes[0]
                    ]
                )

            nominal_damage = sum(
                candidate.damage
                for candidate
                in phase_candidates
            )

            max_hp = (
                boss_hp_by_phase_id[
                    boss_phase_id
                ]
            )

            effective_damage = min(
                nominal_damage,
                max_hp,
            )

            overkill_damage = max(
                0,
                nominal_damage - max_hp,
            )

            boss_plans.append(
                BossOptimizationPlan(
                    boss_id=reference.boss_id,
                    boss_phase_id=(
                        boss_phase_id
                    ),
                    phase_no=(
                        reference.phase_no
                    ),
                    max_hp=max_hp,
                    selected_candidates=tuple(
                        phase_candidates
                    ),
                    nominal_damage=(
                        nominal_damage
                    ),
                    effective_damage=(
                        effective_damage
                    ),
                    overkill_damage=(
                        overkill_damage
                    ),
                )
            )

        total_nominal = sum(
            candidate.damage
            for candidate in selected
        )

        total_effective_result = sum(
            plan.effective_damage
            for plan in boss_plans
        )

        return UnionOptimizationResult(
            selected_candidates=tuple(
                selected
            ),
            boss_plans=tuple(
                boss_plans
            ),
            attack_count=len(
                selected
            ),
            total_nominal_damage=(
                total_nominal
            ),
            total_effective_damage=(
                total_effective_result
            ),
        )

    def _validate_boss_hp(
        self,
        candidates: list[
            OptimizationCandidate
        ],
        boss_hp_by_phase_id: dict[
            int,
            int,
        ],
    ) -> None:
        """Boss HP入力を検証する。"""

        required_phase_ids = {
            candidate.boss_phase_id
            for candidate in candidates
        }

        missing = (
            required_phase_ids
            - set(
                boss_hp_by_phase_id
            )
        )

        if missing:
            raise ValueError(
                (
                    "Boss HPが未指定の"
                    "boss_phase_idがあります: "
                    f"{sorted(missing)}"
                )
            )

        for (
            boss_phase_id,
            hp,
        ) in boss_hp_by_phase_id.items():
            if hp <= 0:
                raise ValueError(
                    (
                        "Boss HPは1以上である"
                        "必要があります: "
                        f"boss_phase_id="
                        f"{boss_phase_id}"
                    )
                )