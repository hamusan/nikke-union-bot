from bot.services import RaidService


def main() -> None:
    service = RaidService()

    raid = service.create_raid(
        "テストユニオンレイド"
    )

    print()
    print(
        f"Raid created: "
        f"{raid.id} / {raid.name}"
    )

    bosses = [
        (1, "Boss 1", 50_000_000_000),
        (2, "Boss 2", 60_000_000_000),
        (3, "Boss 3", 70_000_000_000),
        (4, "Boss 4", 80_000_000_000),
        (5, "Boss 5", 100_000_000_000),
    ]

    for boss_no, name, hp in bosses:
        service.set_boss(
            boss_no=boss_no,
            name=name,
            max_hp=hp,
        )

    service.set_current_hp(
        boss_no=1,
        current_hp=12_500_000_000,
    )

    print()
    print("Boss List")
    print("-----------------------------")

    for boss in service.list_bosses():
        print(
            f"Boss {boss.boss_no}: "
            f"{boss.name}"
        )
        print(
            f"  HP: "
            f"{boss.current_hp:,}"
            f" / "
            f"{boss.max_hp:,}"
        )


if __name__ == "__main__":
    main()