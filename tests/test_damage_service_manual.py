from bot.services import (
    DamageService,
    RaidService,
)


DISCORD_ID = "507895244340068364"

TEAM_NAME = "1"

BOSS_NO = 1

DAMAGE = 8_000_000_000


def main() -> None:
    damage_service = DamageService()
    raid_service = RaidService()

    print()
    print("登録前")
    print("--------------------")

    bosses = raid_service.list_bosses()

    boss_before = next(
        boss
        for boss in bosses
        if boss.boss_no == BOSS_NO
    )

    print(
        f"Boss {boss_before.boss_no}: "
        f"{boss_before.current_hp:,}"
    )

    record, boss_after = (
        damage_service.register_damage(
            discord_id=DISCORD_ID,
            team_name=TEAM_NAME,
            boss_no=BOSS_NO,
            damage=DAMAGE,
        )
    )

    print()
    print("Damage登録")
    print("--------------------")

    print(
        f"DamageRecord ID: {record.id}"
    )

    print(
        f"Damage: {record.damage:,}"
    )

    print()
    print("登録後")
    print("--------------------")

    print(
        f"Boss {boss_after.boss_no}: "
        f"{boss_after.current_hp:,}"
    )


if __name__ == "__main__":
    main()
