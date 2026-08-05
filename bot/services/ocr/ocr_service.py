from pathlib import Path

from paddleocr import PaddleOCR

from bot.services.ocr.result_parser import (
    BattleOcrResult,
    BattleResultParser,
)


class BattleOcrService:
    """戦闘結果画像のOCR処理を担当するService。"""

    def __init__(self) -> None:
        self._ocr: PaddleOCR | None = None
        self._parser = BattleResultParser()

    def _get_ocr(self) -> PaddleOCR:
        """必要になった時点でPaddleOCRを初期化する。"""

        if self._ocr is None:
            self._ocr = PaddleOCR(
                device="cpu",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )

        return self._ocr

    def analyze_image(
        self,
        image_path: Path,
        known_boss_names: list[str],
    ) -> BattleOcrResult:
        """画像からBoss名・最大HP・Damageを取得する。"""

        ocr = self._get_ocr()

        results = ocr.predict(
            str(image_path)
        )

        for result in results:
            data = result.json["res"]

            texts = [
                str(text)
                for text in data.get(
                    "rec_texts",
                    [],
                )
            ]

            scores = [
                float(score)
                for score in data.get(
                    "rec_scores",
                    [],
                )
            ]

            return self._parser.parse(
                texts=texts,
                scores=scores,
                known_boss_names=known_boss_names,
            )

        return BattleOcrResult(
            boss_name=None,
            boss_name_confidence=None,
            boss_max_hp=None,
            boss_max_hp_confidence=None,
            total_damage=None,
            total_damage_confidence=None,
        )