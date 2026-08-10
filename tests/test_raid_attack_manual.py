from bot.services.raid_attack_service import (
    RaidAttackService,
)


RAID_ID = 1
BOSS_ID = 1
PLAYER_ID = 1
TEAM_ID = 1

PHASE_NO = 3
DAMAGE = 12_345_678_900

# 実Discord IDではなく手動テスト専用のダミー値
SOURCE_MESSAGE_ID = 9_990_000_001

# SHA-256形式の64文字ダミー値
IMAGE_SHA256 = "a" * 64


def main() -> None:
    service = RaidAttackService()

    print("=== RaidAttack Manual Test ===")
    print()

    # --------------------------------
    # 1. 新規登録
    # --------------------------------

    first = service.record_attack(
        raid_id=RAID_ID,
        phase_no=PHASE_NO,
        boss_id=BOSS_ID,
        player_id=PLAYER_ID,
        team_id=TEAM_ID,
        damage=DAMAGE,
        source_message_id=(
            SOURCE_MESSAGE_ID
        ),
        image_sha256=(
            IMAGE_SHA256
        ),
    )

    assert first.created is True

    assert (
        first.attack.raid_id
        == RAID_ID
    )

    assert (
        first.attack.phase_no
        == PHASE_NO
    )

    assert (
        first.attack.boss_id
        == BOSS_ID
    )

    assert (
        first.attack.player_id
        == PLAYER_ID
    )

    assert (
        first.attack.team_id
        == TEAM_ID
    )

    assert (
        first.attack.damage
        == DAMAGE
    )

    print(
        "[OK] first attack created"
    )

    print(
        "attack_id =",
        first.attack.attack_id,
    )

    # --------------------------------
    # 2. 同じDiscord Messageで再登録
    # --------------------------------

    second = service.record_attack(
        raid_id=RAID_ID,
        phase_no=PHASE_NO,
        boss_id=BOSS_ID,
        player_id=PLAYER_ID,
        team_id=TEAM_ID,
        damage=DAMAGE,
        source_message_id=(
            SOURCE_MESSAGE_ID
        ),
        image_sha256=(
            IMAGE_SHA256
        ),
    )

    assert second.created is False

    assert (
        second.attack.attack_id
        == first.attack.attack_id
    )

    print(
        "[OK] duplicate source_message_id prevented"
    )

    # --------------------------------
    # 3. RaidAttack一覧
    # --------------------------------

    attacks = service.list_by_raid(
        RAID_ID
    )

    matching = [
        attack
        for attack in attacks
        if (
            attack.attack_id
            == first.attack.attack_id
        )
    ]

    assert len(matching) == 1

    print(
        "[OK] attack exists in raid history"
    )

    print(
        "raid attack count =",
        len(attacks),
    )

    print()
    print(
        "RaidAttack TEST OK"
    )


if __name__ == "__main__":
    main()