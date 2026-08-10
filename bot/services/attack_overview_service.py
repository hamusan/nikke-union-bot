from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from bot.core.database import session_scope
from bot.models.player import Player
from bot.models.raid import Raid
from bot.models.raid_attack import RaidAttack
from bot.models.raid_attack_cancellation import (
    RaidAttackCancellation,
)
from bot.models.team import Team


@dataclass(
    frozen=True
)
class AttackTeamOverview:
    """実凸管理画面に表示する1編成。"""

    raid_id: int

    player_id: int
    player_name: str
    player_discord_id: str

    team_id: int
    team_no: int
    team_name: str | None

    character_names: tuple[
        str,
        ...
    ]

    raid_attack_id: int | None

    @property
    def attacked(
        self,
    ) -> bool:
        return (
            self.raid_attack_id
            is not None
        )


@dataclass(
    frozen=True
)
class AttackOverviewResult:
    """実凸管理一覧。"""

    raid_id: int
    raid_name: str
    current_phase: int

    target: str

    teams: tuple[
        AttackTeamOverview,
        ...
    ]


class AttackOverviewService:
    """
    /attack 用の編成一覧を取得する。
    """

    ALL_TARGET = "all"

    def autocomplete_targets(
        self,
        current: str,
        limit: int = 25,
    ) -> tuple[str, ...]:
        """
        /attack target 用Autocomplete。

        All + 有効Playerのnicknameを返す。
        """

        if limit <= 0:
            return ()

        normalized = (
            current
            .strip()
            .casefold()
        )

        with session_scope() as session:
            nicknames = list(
                session.scalars(
                    select(
                        Player.nickname
                    )
                    .where(
                        Player.active.is_(True)
                    )
                    .order_by(
                        Player.nickname
                    )
                ).all()
            )

        results: list[str] = []

        # --------------------------------
        # All
        # --------------------------------

        if (
            not normalized
            or normalized in "all"
        ):
            results.append(
                "All"
            )

        # --------------------------------
        # Player nickname
        # --------------------------------

        seen = {
            "all"
        }

        for nickname in nicknames:
            name = nickname.strip()

            if not name:
                continue

            key = name.casefold()

            if key in seen:
                continue

            seen.add(
                key
            )

            # 入力中なら部分一致
            if (
                normalized
                and normalized
                not in key
            ):
                continue

            results.append(
                name
            )

            if len(results) >= limit:
                break

        return tuple(
            results[:limit]
        )

    def build(
        self,
        target: str,
    ) -> AttackOverviewResult:
        """
        target:
            "All"
            または
            Player.nickname

        大文字小文字は区別しない。
        """

        normalized_target = (
            target.strip()
        )

        if not normalized_target:
            raise ValueError(
                "targetを指定してください。"
            )

        with session_scope() as session:
            # --------------------------------
            # Active Raid
            # --------------------------------

            raid = session.scalar(
                select(
                    Raid
                )
                .where(
                    Raid.active.is_(True)
                )
                .order_by(
                    Raid.id.desc()
                )
            )

            if raid is None:
                raise ValueError(
                    "Active Raidがありません。"
                )

            # --------------------------------
            # Player
            # --------------------------------

            player_statement = (
                select(
                    Player
                )
                .where(
                    Player.active.is_(True)
                )
                .order_by(
                    Player.nickname,
                    Player.id,
                )
            )

            players = list(
                session.scalars(
                    player_statement
                ).all()
            )

            if (
                normalized_target.casefold()
                != self.ALL_TARGET
            ):
                target_key = (
                    normalized_target
                    .casefold()
                )

                players = [
                    player
                    for player in players
                    if player.nickname
                    .strip()
                    .casefold()
                    == target_key
                ]

                if not players:
                    raise ValueError(
                        (
                            "Playerが"
                            "見つかりません: "
                            f"{normalized_target}"
                        )
                    )

            player_ids = {
                player.id
                for player in players
            }

            # --------------------------------
            # Team
            # --------------------------------

            if player_ids:
                teams = list(
                    session.scalars(
                        select(
                            Team
                        )
                        .where(
                            Team.player_id.in_(
                                player_ids
                            )
                        )
                        .where(
                            Team.active.is_(True)
                        )
                        .order_by(
                            Team.player_id,
                            Team.team_no,
                        )
                    ).all()
                )
            else:
                teams = []

            # --------------------------------
            # RaidAttack
            # --------------------------------

            attacks = list(
                session.scalars(
                    select(
                        RaidAttack
                    )
                    .where(
                        RaidAttack.raid_id
                        == raid.id
                    )
                    .order_by(
                        RaidAttack.id
                    )
                ).all()
            )

            attack_ids = [
                attack.id
                for attack in attacks
            ]

            # --------------------------------
            # Cancellation
            # --------------------------------

            cancelled_attack_ids: set[
                int
            ] = set()

            if attack_ids:
                cancelled_attack_ids = set(
                    session.scalars(
                        select(
                            RaidAttackCancellation
                            .raid_attack_id
                        )
                        .where(
                            RaidAttackCancellation
                            .raid_attack_id
                            .in_(
                                attack_ids
                            )
                        )
                    ).all()
                )

            # --------------------------------
            # 有効なRaidAttackを
            # Teamごとに整理
            # --------------------------------

            attacks_by_team: dict[
                int,
                list[RaidAttack],
            ] = {}

            for attack in attacks:
                if (
                    attack.id
                    in cancelled_attack_ids
                ):
                    continue

                attacks_by_team.setdefault(
                    attack.team_id,
                    [],
                ).append(
                    attack
                )

            player_by_id = {
                player.id: player
                for player in players
            }

            overview_teams: list[
                AttackTeamOverview
            ] = []

            for team in teams:
                player = (
                    player_by_id.get(
                        team.player_id
                    )
                )

                if player is None:
                    continue

                active_attacks = (
                    attacks_by_team.get(
                        team.id,
                        [],
                    )
                )

                # 1Raidにつき、
                # 同じTeamは1実凸だけという
                # 今回の仕様。
                if len(active_attacks) > 1:
                    raise RuntimeError(
                        (
                            "同じTeamに複数の"
                            "有効RaidAttackがあります: "
                            f"team_id={team.id}, "
                            f"attack_ids="
                            f"{[
                                attack.id
                                for attack
                                in active_attacks
                            ]}"
                        )
                    )

                raid_attack_id = (
                    active_attacks[0].id
                    if active_attacks
                    else None
                )

                character_names = tuple(
                    member.character.name
                    for member
                    in team.members
                )

                overview_teams.append(
                    AttackTeamOverview(
                        raid_id=raid.id,

                        player_id=(
                            player.id
                        ),
                        player_name=(
                            player.nickname
                        ),
                        player_discord_id=(
                            player.discord_id
                        ),

                        team_id=team.id,
                        team_no=(
                            team.team_no
                        ),
                        team_name=(
                            team.team_name
                        ),

                        character_names=(
                            character_names
                        ),

                        raid_attack_id=(
                            raid_attack_id
                        ),
                    )
                )

            overview_teams.sort(
                key=lambda item: (
                    item.player_name.casefold(),
                    item.player_id,
                    item.team_no,
                )
            )

            return AttackOverviewResult(
                raid_id=raid.id,
                raid_name=raid.name,
                current_phase=(
                    raid.current_phase
                ),
                target=normalized_target,
                teams=tuple(
                    overview_teams
                ),
            )