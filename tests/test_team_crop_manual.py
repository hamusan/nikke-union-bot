from pathlib import Path

import cv2

from bot.services.team_image import (
    TeamPortraitCropper,
)


INPUT_IMAGE = Path(
    "uploads/team_test.png"
)

OUTPUT_DIR = Path(
    "uploads/team_crop_debug"
)


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    cropper = TeamPortraitCropper()

    result = cropper.crop(
        INPUT_IMAGE
    )

    print()
    print("戦闘履歴パネル")
    print("--------------------------")

    print(
        "panel:",
        result.panel_box,
    )

    print()
    print("キャラ切り出し")
    print("--------------------------")

    for index, portrait in enumerate(
        result.portraits,
        start=1,
    ):
        output_path = (
            OUTPUT_DIR
            / f"slot_{index}.png"
        )

        cv2.imwrite(
            str(output_path),
            portrait,
        )

        print(
            f"slot {index}: "
            f"{output_path}"
        )


if __name__ == "__main__":
    main()