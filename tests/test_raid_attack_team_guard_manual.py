from __future__ import annotations

from bot.services.attack_candidate_service import (
    AttackCandidateService,
)
from bot.services.attack_overview_service import (
    AttackOverviewService,
)
from bot.services.raid_attack_cancellation_coordinator_service import (
    RaidAttackCancellationCoordinatorService,
)
from bot.services.raid_attack_coordinator_service import (
    RaidAttackCoordinatorService,
)


def main() -> None:
    overview_service = (
        AttackOverviewService()
    )

    candidate_service = (
        AttackCandidateService()
    )

    attack_service = (
        RaidAttackCoordinatorService()
    )

    cancellation_service = (
        RaidAttackCancellationCoordinatorService()
    )

    overview = overview_service.build(
        "All"
    )

    if not overview.teams:
        print(
            "[SKIP] Teamがありません。"
        )
        return

    target = overview.teams[0]

    candidate_result = (
        candidate_service.get_for_team(
            target.team_id
        )
    )

    if not candidate_result.candidates:
        print(
            "[SKIP] "
            "現在PhaseのDamageRecordが"
            "ありません。"
        )
        return

    candidate = (
        candidate_result.candidates[0]
    )

    created_for_test = False
    test_attack_id: int | None = None

    try:
        # --------------------------------
        # まだ未凸なら、
        # テスト用に1凸だけ登録
        # --------------------------------

        if not candidate_result.attacked:
            first = attack_service.record_attack(
                raid_id=(
                    candidate.raid_id
                ),
                boss_id=(
                    candidate.boss_id
                ),
                player_id=(
                    candidate.player_id
                ),
                team_id=(
                    candidate.team_id
                ),
                damage=(
                    candidate.damage
                ),
                source_message_id=None,
                image_sha256=None,
                expected_phase_no=(
                    candidate.phase_no
                ),
            )

            test_attack_id = (
                first.attack
                .attack.attack_id
            )

            created_for_test = True

            print(
                "[OK] first attack created"
            )

            print(
                "RaidAttack ID =",
                test_attack_id,
            )

        else:
            test_attack_id = (
                candidate_result
                .active_raid_attack_id
            )

            print(
                "Existing RaidAttack ID =",
                test_attack_id,
            )

        # --------------------------------
        # 同じTeamでもう一度登録
        # → 必ず拒否されること
        # --------------------------------

        try:
            attack_service.record_attack(
                raid_id=(
                    candidate.raid_id
                ),
                boss_id=(
                    candidate.boss_id
                ),
                player_id=(
                    candidate.player_id
                ),
                team_id=(
                    candidate.team_id
                ),
                damage=(
                    candidate.damage
                ),
                source_message_id=None,
                image_sha256=None,
                expected_phase_no=(
                    candidate.phase_no
                ),
            )

        except ValueError as error:
            message = str(
                error
            )

            print(
                "[OK] duplicate team attack rejected"
            )

            print(
                "Message =",
                message,
            )

            assert (
                "すでに"
                in message
            )

        else:
            raise AssertionError(
                (
                    "同じTeamのRaidAttackが"
                    "二重登録されてしまいました。"
                )
            )

        print()
        print(
            "RaidAttack Team Guard TEST OK"
        )

    finally:
        # --------------------------------
        # このテスト自身が作ったAttackだけ
        # 取消して元へ戻す
        # --------------------------------

        if (
            created_for_test
            and test_attack_id is not None
        ):
            cancellation_service.cancel_attack(
                raid_attack_id=(
                    test_attack_id
                ),
                cancelled_by_discord_id=(
                    "manual-test"
                ),
                reason=(
                    "team guard manual test cleanup"
                ),
            )

            print(
                "[CLEANUP] "
                "test RaidAttack cancelled "
                "and Raid rebuilt"
            )


if __name__ == "__main__":
    main()