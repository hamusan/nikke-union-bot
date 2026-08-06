from pathlib import Path

from bot.services import TeamService
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

DISCORD_ID = "ここに自分のDiscord ID"

DISCORD_NAME = "テストユーザー"


def main() -> None:
    cropper = TeamPortraitCropper()

    recognizer = CharacterRecognizer(
        template_dir=TEMPLATE_DIR
    )

    team_service = TeamService()

    crop_result = cropper.crop(
        INPUT_IMAGE
    )

    character_names: list[str] = []

    print()
    print("画像認識")
    print("--------------------------------")

    for index, portrait in enumerate(
        crop_result.portraits,
        start=1,
    ):
        result = recognizer.recognize(
            portrait
        )

        if result.character_name is None:
            raise RuntimeError(
                f"Slot {index} のキャラを"
                "判定できませんでした。"
            )

        character_names.append(
            result.character_name
        )

        print(
            f"{index}. "
            f"{result.character_name} "
            f"({result.confidence:.3f})"
        )

    print()
    print("編成判定")
    print("--------------------------------")

    team, created = (
        team_service.find_or_create_team_from_characters(
            discord_id=DISCORD_ID,
            discord_name=DISCORD_NAME,
            character_names=character_names,
        )
    )

    if created:
        print(
            f"新しい編成 #{team.team_no} "
            "として登録しました。"
        )
    else:
        print(
            f"既存の編成 #{team.team_no} "
            "と一致しました。"
        )

    print()
    print("構成")
    print("--------------------------------")

    for member in team.members:
        print(
            f"{member.position}. "
            f"{member.character.name}"
        )


if __name__ == "__main__":
    main()