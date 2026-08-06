from dataclasses import dataclass
from collections import defaultdict

from ortools.sat.python import cp_model

from bot.services.optimization.candidate import (
    OptimizationCandidate,
)


@dataclass(frozen=True)
class OptimizationResult:
    """1プレイヤー分の最適化結果。"""

    player_id: int

    selected_candidates: tuple[
        OptimizationCandidate,
        ...
    ]

    total_damage: int


class PlayerOptimizationSolver:
    """
    1プレイヤー分の攻撃候補から、
    最大3凸の最適な組み合わせを選択する。
    """

    def solve(
        self,
        player_id: int,
        candidates: list[
            OptimizationCandidate
        ],
        max_attacks: int = 3,
    ) -> OptimizationResult:
        """
        制約:
        - 最大 max_attacks 回まで
        - 同じTeamは最大1回
        - 同じCharacterは最大1回

        目的:
        - 合計Damage最大化
        """

        player_candidates = [
            candidate
            for candidate in candidates
            if candidate.player_id == player_id
        ]

        if not player_candidates:
            return OptimizationResult(
                player_id=player_id,
                selected_candidates=(),
                total_damage=0,
            )

        model = cp_model.CpModel()

        # candidateごとに
        # 「採用する / 採用しない」のBool変数。
        variables: dict[int, cp_model.IntVar] = {}

        for index, candidate in enumerate(
            player_candidates
        ):
            variables[index] = (
                model.NewBoolVar(
                    f"candidate_{index}"
                )
            )

        # ------------------------------
        # 制約1:
        # 最大3凸
        # ------------------------------

        model.Add(
            sum(
                variables.values()
            )
            <= max_attacks
        )

        # ------------------------------
        # 制約2:
        # 同じTeamを複数回使わない
        # ------------------------------

        team_candidate_indexes: dict[
            int,
            list[int],
        ] = defaultdict(list)

        for index, candidate in enumerate(
            player_candidates
        ):
            team_candidate_indexes[
                candidate.team_id
            ].append(
                index
            )

        for indexes in (
            team_candidate_indexes.values()
        ):
            model.Add(
                sum(
                    variables[index]
                    for index in indexes
                )
                <= 1
            )

        # ------------------------------
        # 制約3:
        # 同じCharacterを複数凸で使わない
        # ------------------------------

        character_candidate_indexes: dict[
            int,
            list[int],
        ] = defaultdict(list)

        for index, candidate in enumerate(
            player_candidates
        ):
            for character_id in (
                candidate.character_ids
            ):
                character_candidate_indexes[
                    character_id
                ].append(
                    index
                )

        for indexes in (
            character_candidate_indexes.values()
        ):
            model.Add(
                sum(
                    variables[index]
                    for index in indexes
                )
                <= 1
            )

        # ------------------------------
        # 目的関数:
        # 合計Damage最大化
        # ------------------------------

        model.Maximize(
            sum(
                candidate.damage
                * variables[index]
                for index, candidate in enumerate(
                    player_candidates
                )
            )
        )

        # ------------------------------
        # Solver実行
        # ------------------------------

        solver = cp_model.CpSolver()

        status = solver.Solve(
            model
        )

        if status not in (
            cp_model.OPTIMAL,
            cp_model.FEASIBLE,
        ):
            return OptimizationResult(
                player_id=player_id,
                selected_candidates=(),
                total_damage=0,
            )

        selected: list[
            OptimizationCandidate
        ] = []

        for index, candidate in enumerate(
            player_candidates
        ):
            if solver.Value(
                variables[index]
            ) == 1:
                selected.append(
                    candidate
                )

        # Damageが大きい順に表示。
        selected.sort(
            key=lambda candidate: (
                candidate.damage
            ),
            reverse=True,
        )

        total_damage = sum(
            candidate.damage
            for candidate in selected
        )

        return OptimizationResult(
            player_id=player_id,
            selected_candidates=tuple(
                selected
            ),
            total_damage=total_damage,
        )