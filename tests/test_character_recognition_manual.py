from pathlib import Path

from bot.services.team_image import (
    CharacterRecognizer,
    TeamPortraitCropper,
)


INPUT_IMAGE = Path(
    "uploads/team_test.png"
)

TEMPLATE_DIR = Path(
    "uploads/character_templates"
)


def main() -> None:
    cropper = TeamPortraitCropper()

    recognizer = CharacterRecognizer(
        template_dir=TEMPLATE_DIR
    )

    crop_result = cropper.crop(
        INPUT_IMAGE
    )

    print()
    print("キャラ認識結果")
    print("--------------------------------")

    for index, portrait in enumerate(
        crop_result.portraits,
        start=1,
    ):
        result = recognizer.recognize(
            portrait
        )

        print()
        print(
            f"Slot {index}"
        )

        if result.character_name is None:
            print(
                "  判定: 不明"
            )
        else:
            print(
                f"  判定: "
                f"{result.character_name}"
            )

        print(
            f"  Confidence: "
            f"{result.confidence:.3f}"
        )

        print(
            "  候補:"
        )

        for candidate in (
            result.candidates
        ):
            print(
                f"    "
                f"{candidate.name}: "
                f"{candidate.score:.3f}"
            )


if __name__ == "__main__":
    main()