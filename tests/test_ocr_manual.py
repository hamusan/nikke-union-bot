from pathlib import Path

from paddleocr import PaddleOCR

from bot.services.ocr import BattleResultParser


SCREENSHOT_DIR = Path(
    "uploads/screenshots"
)

OUTPUT_DIR = Path(
    "uploads/ocr_debug"
)


def find_latest_image() -> Path:
    """最新のスクリーンショットを取得する。"""

    image_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    }

    images = [
        path
        for path in SCREENSHOT_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() in image_extensions
    ]

    if not images:
        raise RuntimeError(
            "uploads/screenshots に画像がありません。"
        )

    return max(
        images,
        key=lambda path: path.stat().st_mtime,
    )


def main() -> None:
    image_path = find_latest_image()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("OCRテスト")
    print("------------------------------")
    print(f"画像: {image_path}")
    print()

    ocr = PaddleOCR(
        device="cpu",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )

    results = ocr.predict(
        str(image_path)
    )

    parser = BattleResultParser()

    print()
    print("OCR結果")
    print("------------------------------")

    for result in results:
        data = result.json["res"]

        texts = list(
            data["rec_texts"]
        )

        scores = [
            float(score)
            for score in data["rec_scores"]
        ]

        for text, score in zip(
            texts,
            scores,
        ):
            print(
                f"{score:.3f} | {text}"
            )

        parsed = parser.parse(
            texts=texts,
            scores=scores,
            known_boss_names=[
                "リビルドオベリスク",
            ],
        )

        print()
        print("抽出結果")
        print("------------------------------")

        print(
            "BOSS:",
            parsed.boss_name
            or "取得失敗",
        )

        print(
            "BOSS 信頼度:",
            parsed.boss_name_confidence,
        )

        print(
            "MAX HP:",
            (
                f"{parsed.boss_max_hp:,}"
                if parsed.boss_max_hp is not None
                else "取得失敗"
            ),
        )

        print(
            "MAX HP 信頼度:",
            parsed.boss_max_hp_confidence,
        )

        print(
            "TOTAL DAMAGE:",
            (
                f"{parsed.total_damage:,}"
                if parsed.total_damage is not None
                else "取得失敗"
            ),
        )

        print(
            "TOTAL DAMAGE 信頼度:",
            parsed.total_damage_confidence,
        )

        result.save_to_img(
            str(OUTPUT_DIR)
        )

        result.save_to_json(
            str(OUTPUT_DIR)
        )

    print()
    print("OCR結果")
    print("------------------------------")

    for result in results:
        result.print()

        result.save_to_img(
            str(OUTPUT_DIR)
        )

        result.save_to_json(
            str(OUTPUT_DIR)
        )

    print()
    print(
        "OCRデバッグ結果を "
        "uploads/ocr_debug に保存しました。"
    )


if __name__ == "__main__":
    main()