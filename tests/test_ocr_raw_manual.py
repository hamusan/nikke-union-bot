from pathlib import Path

from bot.services.ocr import BattleOcrService


TEST_IMAGE = Path(
    r"uploads\screenshots\1534795277670678661_1534795277129617529.png"
)


def main() -> None:
    service = BattleOcrService()

    image = service._load_image(
        TEST_IMAGE
    )

    ocr = service._get_ocr()

    results = ocr.predict(
        image
    )

    print()
    print("OCR RAW DEBUG")
    print("=" * 60)

    for result_index, result in enumerate(
        results,
        start=1,
    ):
        data = result.json["res"]

        print()
        print(
            f"Result #{result_index}"
        )

        print()
        print("keys:")
        print(
            list(data.keys())
        )

        texts = data.get(
            "rec_texts",
            [],
        )

        scores = data.get(
            "rec_scores",
            [],
        )

        boxes = data.get(
            "rec_boxes",
            [],
        )

        print()
        print("認識結果")
        print("-" * 60)

        for index, text in enumerate(
            texts
        ):
            score = (
                scores[index]
                if index < len(scores)
                else None
            )

            box = (
                boxes[index]
                if index < len(boxes)
                else None
            )

            print(
                f"[{index:02d}] "
                f"text={text!r}"
            )

            print(
                f"     score={score}"
            )

            print(
                f"     box={box}"
            )


if __name__ == "__main__":
    main()