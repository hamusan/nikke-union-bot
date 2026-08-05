from bot.services import RaidService


BOSS_NO = 1

BOSS_NAME = "リビルドオベリスク"

PHASE_NO = 3

MAX_HP = 149_784_418_800


def main() -> None:
    service = RaidService()

    phase = service.set_boss_phase(
        boss_no=BOSS_NO,
        phase_no=PHASE_NO,
        max_hp=MAX_HP,
    )

    print()
    print("Phase登録")
    print("------------------------------")

    print(
        f"Boss ID : {phase.boss_id}"
    )

    print(
        f"Phase   : {phase.phase_no}"
    )

    print(
        f"Max HP  : {phase.max_hp:,}"
    )

    resolved = service.resolve_boss_phase(
        boss_name=BOSS_NAME,
        max_hp=MAX_HP,
    )

    print()
    print("Phase自動判定")
    print("------------------------------")

    print(
        f"Boss  : {BOSS_NAME}"
    )

    print(
        f"Max HP: {MAX_HP:,}"
    )

    print(
        f"Phase : {resolved.phase_no}"
    )


if __name__ == "__main__":
    main()