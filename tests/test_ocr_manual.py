from pathlib import Path

from bot.services import RaidService
from bot.services.ocr import BattleOcrService


SCREENSHOT_DIR = Path(
    "uploads/screenshots"
)


def get_latest_image() -> Path:
    """uploads/screenshots 内の最新画像を取得する。"""

    extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    }

    images = [
        path
        for path in SCREENSHOT_DIR.iterdir()
        if (
            path.is_file()
            and path.suffix.lower() in extensions
        )
    ]

    if not images:
        raise FileNotFoundError(
            "uploads/screenshots に画像がありません。"
        )

    return max(
        images,
        key=lambda path: path.stat().st_mtime,
    )


def main() -> None:
    test_image = get_latest_image()

    print()
    print("OCRテスト")
    print("------------------------------")
    print(f"画像: {test_image}")
    print()

    raid_service = RaidService()

    bosses = raid_service.list_bosses()

    known_boss_names = [
        boss.name
        for boss in bosses
    ]

    for boss in bosses:
        phases = (
            raid_service.list_boss_phases(
                boss.boss_no
            )
        )

    print("登録済みBoss:")
    for boss_name in known_boss_names:
        print(
            f"  - {boss_name}"
        )

    print()

    ocr_service = BattleOcrService()

    result = ocr_service.analyze_image(
        image_path=test_image,
        known_boss_names=known_boss_names,
    )

    print()
    print("OCR結果")
    print("------------------------------")

    print(
        "Boss:",
        result.boss_name,
    )

    print(
        "Boss confidence:",
        result.boss_name_confidence,
    )

    print(
        "最大HP:",
        (
            f"{result.boss_max_hp:,}"
            if result.boss_max_hp is not None
            else None
        ),
    )

    print(
        "最大HP confidence:",
        result.boss_max_hp_confidence,
    )

    print(
        "Damage:",
        (
            f"{result.total_damage:,}"
            if result.total_damage is not None
            else None
        ),
    )

    print(
        "Damage confidence:",
        result.total_damage_confidence,
    )


if __name__ == "__main__":
    main()