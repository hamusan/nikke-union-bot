from dataclasses import replace
from pathlib import Path
import re

import cv2
import numpy as np
from paddleocr import PaddleOCR

from bot.services.ocr.result_parser import (
    BattleOcrResult,
    BattleResultParser,
)


OCR_DEBUG_DIR = Path(
    "uploads/ocr_debug"
)


class BattleOcrService:
    """NIKKE戦闘結果スクリーンショットのOCRサービス。"""

    def __init__(self) -> None:
        self._ocr: PaddleOCR | None = None
        self._parser = BattleResultParser()

        OCR_DEBUG_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _get_ocr(self) -> PaddleOCR:
        """PaddleOCRを遅延初期化する。"""

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
        """
        戦闘結果画像を解析する。

        1回目:
            画像全体をOCR。

        2回目:
            "/最大HP" 部分だけ切り出して拡大し、
            最大HP専用OCRを実行する。
        """

        image = self._load_image(
            image_path
        )

        ocr = self._get_ocr()

        results = ocr.predict(
            image
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

            boxes = data.get(
                "rec_boxes",
                [],
            )

            parsed = self._parser.parse(
                texts=texts,
                scores=scores,
                boxes=boxes,
                known_boss_names=known_boss_names,
            )

            # 最大HP部分だけ再OCRする。
            refined_hp = (
                self._refine_max_hp(
                    image=image,
                    image_path=image_path,
                    texts=texts,
                    boxes=boxes,
                )
            )

            if refined_hp is not None:
                (
                    refined_value,
                    refined_confidence,
                ) = refined_hp

                parsed = replace(
                    parsed,
                    boss_max_hp=refined_value,
                    boss_max_hp_confidence=(
                        refined_confidence
                    ),
                )

            return parsed

        return BattleOcrResult(
            boss_name=None,
            boss_name_confidence=None,
            boss_max_hp=None,
            boss_max_hp_confidence=None,
            total_damage=None,
            total_damage_confidence=None,
        )

    def _refine_max_hp(
        self,
        image: np.ndarray,
        image_path: Path,
        texts: list[str],
        boxes,
    ) -> tuple[int, float | None] | None:
        """
        1回目OCRで見つけた最大HPの領域だけを
        切り出して再OCRする。
        """

        max_hp_box = self._find_max_hp_box(
            texts=texts,
            boxes=boxes,
        )

        if max_hp_box is None:
            return None

        crop = self._crop_max_hp(
            image=image,
            box=max_hp_box,
        )

        if crop is None:
            return None

        # デバッグ用に元の切り出し画像も保存。
        raw_debug_path = (
            OCR_DEBUG_DIR
            / f"{image_path.stem}_max_hp_raw.png"
        )

        cv2.imwrite(
            str(raw_debug_path),
            crop,
        )

        variants = self._create_max_hp_variants(
            crop
        )

        candidates: list[
            tuple[int, float | None]
        ] = []

        for variant_index, variant in enumerate(
            variants,
            start=1,
        ):
            debug_path = (
                OCR_DEBUG_DIR
                / (
                    f"{image_path.stem}"
                    f"_max_hp_variant_"
                    f"{variant_index}.png"
                )
            )

            cv2.imwrite(
                str(debug_path),
                variant,
            )

            candidate = (
                self._ocr_max_hp_crop(
                    variant
                )
            )

            if candidate is not None:
                candidates.append(
                    candidate
                )

        if not candidates:
            return None

        # 複数の前処理結果がある場合、
        # 桁数が多い値を優先する。
        #
        # 同じ桁数ならOCR confidenceが
        # 高いものを採用する。
        best = max(
            candidates,
            key=lambda item: (
                len(str(item[0])),
                (
                    item[1]
                    if item[1] is not None
                    else 0.0
                ),
            ),
        )

        return best

    def _find_max_hp_box(
        self,
        texts: list[str],
        boxes,
    ):
        """
        HP Remaining と TOTAL DAMAGE の間から
        最大HPのboxを探す。

        優先順位:
        1. "/数字"
        2. "／数字"
        3. "/" 単独の右隣にある数値
        4. 一番右側の数値
        """

        hp_index = self._find_label_index(
            texts=texts,
            label="HPREMAINING",
        )

        damage_index = self._find_label_index(
            texts=texts,
            label="TOTALDAMAGE",
        )

        if (
            hp_index is None
            or damage_index is None
        ):
            return None

        hp_box = self._get_box(
            boxes,
            hp_index,
        )

        damage_box = self._get_box(
            boxes,
            damage_index,
        )

        if (
            hp_box is None
            or damage_box is None
        ):
            return None

        hp_y = self._box_center_y(
            hp_box
        )

        damage_y = self._box_center_y(
            damage_box
        )

        top_y = min(
            hp_y,
            damage_y,
        )

        bottom_y = max(
            hp_y,
            damage_y,
        )

        numeric_candidates = []
        slash_only_candidates = []

        for index, text in enumerate(texts):
            box = self._get_box(
                boxes,
                index,
            )

            if box is None:
                continue

            center_y = self._box_center_y(
                box
            )

            if not (
                top_y < center_y < bottom_y
            ):
                continue

            stripped = text.strip()

            digits = self._digits_only(
                stripped
            )

            # "/150,..." のように
            # slashと最大HPが同じOCRテキスト。
            if (
                (
                    stripped.startswith("/")
                    or stripped.startswith("／")
                )
                and digits
            ):
                return box

            # "/" だけ別認識されたケース。
            if stripped in {
                "/",
                "／",
            }:
                slash_only_candidates.append(
                    (
                        index,
                        box,
                    )
                )
                continue

            if digits:
                numeric_candidates.append(
                    (
                        index,
                        box,
                        center_y,
                    )
                )

        # "/" が単独認識された場合、
        # 同じ行の右側にある数字を探す。
        for _, slash_box in (
            slash_only_candidates
        ):
            slash_x = self._box_center_x(
                slash_box
            )

            slash_y = self._box_center_y(
                slash_box
            )

            candidates = []

            for _, number_box, number_y in (
                numeric_candidates
            ):
                number_x = self._box_center_x(
                    number_box
                )

                if number_x <= slash_x:
                    continue

                vertical_distance = abs(
                    number_y - slash_y
                )

                horizontal_distance = (
                    number_x - slash_x
                )

                candidates.append(
                    (
                        vertical_distance,
                        horizontal_distance,
                        number_box,
                    )
                )

            if candidates:
                _, _, best_box = min(
                    candidates,
                    key=lambda item: (
                        item[0],
                        item[1],
                    ),
                )

                return best_box

        # "/" がOCRされなかった場合。
        #
        # NIKKEの表示は
        # 残HP / 最大HP
        # なので右側の数字を最大HPとみなす。
        if numeric_candidates:
            _, best_box, _ = max(
                numeric_candidates,
                key=lambda item: (
                    self._box_center_x(
                        item[1]
                    )
                ),
            )

            return best_box

        return None

    def _crop_max_hp(
        self,
        image: np.ndarray,
        box,
    ) -> np.ndarray | None:
        """最大HPのOCR box周辺を切り出す。"""

        image_height, image_width = (
            image.shape[:2]
        )

        x1 = int(box[0])
        y1 = int(box[1])
        x2 = int(box[2])
        y2 = int(box[3])

        width = max(
            1,
            x2 - x1,
        )

        height = max(
            1,
            y2 - y1,
        )

        # 左側には残HPがかなり近いため、
        # 横方向の余白は小さめにする。
        padding_left = max(
            2,
            int(width * 0.02),
        )

        padding_right = max(
            8,
            int(width * 0.08),
        )

        # 上下方向には余裕を持たせる。
        padding_y = max(
            8,
            int(height * 0.45),
        )

        crop_x1 = max(
            0,
            x1 - padding_left,
        )

        crop_y1 = max(
            0,
            y1 - padding_y,
        )

        crop_x2 = min(
            image_width,
            x2 + padding_right,
        )

        crop_y2 = min(
            image_height,
            y2 + padding_y,
        )

        crop = image[
            crop_y1:crop_y2,
            crop_x1:crop_x2,
        ]

        if crop.size == 0:
            return None

        return crop

    def _create_max_hp_variants(
        self,
        crop: np.ndarray,
    ) -> list[np.ndarray]:
        """
        最大HP再OCR用の画像を作る。

        Variant 1:
            4倍拡大したカラー画像

        Variant 2:
            グレースケール + コントラスト強調
        """

        scale = 4

        enlarged = cv2.resize(
            crop,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )

        enlarged = cv2.copyMakeBorder(
            enlarged,
            30,
            30,
            30,
            30,
            cv2.BORDER_REPLICATE,
        )

        gray = cv2.cvtColor(
            enlarged,
            cv2.COLOR_BGR2GRAY,
        )

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8),
        )

        enhanced_gray = clahe.apply(
            gray
        )

        enhanced = cv2.cvtColor(
            enhanced_gray,
            cv2.COLOR_GRAY2BGR,
        )

        return [
            enlarged,
            enhanced,
        ]

    def _ocr_max_hp_crop(
        self,
        image: np.ndarray,
    ) -> tuple[int, float | None] | None:
        """
        最大HPの切り出し画像をOCRし、
        数字を1つに再構築する。
        """

        ocr = self._get_ocr()

        results = ocr.predict(
            image
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

            boxes = data.get(
                "rec_boxes",
                [],
            )

            number_parts = []

            for index, text in enumerate(texts):
                digits = self._digits_only(
                    text
                )

                if not digits:
                    continue

                box = self._get_box(
                    boxes,
                    index,
                )

                if box is not None:
                    x_position = float(
                        box[0]
                    )
                else:
                    x_position = float(
                        index
                    )

                score = (
                    scores[index]
                    if index < len(scores)
                    else None
                )

                number_parts.append(
                    (
                        x_position,
                        digits,
                        score,
                    )
                )

            if not number_parts:
                continue

            # 左 → 右へ並べる。
            number_parts.sort(
                key=lambda item: item[0]
            )

            # OCRが
            #
            # "150,841"
            # "811,600"
            #
            # のように分割した場合にも対応する。
            combined_digits = "".join(
                part[1]
                for part in number_parts
            )

            if not combined_digits.isdigit():
                continue

            # 小さすぎる数字を誤って拾うのを防止。
            if len(combined_digits) < 7:
                continue

            value = int(
                combined_digits
            )

            confidence_values = [
                part[2]
                for part in number_parts
                if part[2] is not None
            ]

            confidence: float | None

            if confidence_values:
                # 複数に分割された場合は
                # 一番低いconfidenceを採用。
                #
                # 「全体としての安全側の信頼度」
                # として扱う。
                confidence = min(
                    confidence_values
                )
            else:
                confidence = None

            return (
                value,
                confidence,
            )

        return None

    def _load_image(
        self,
        image_path: Path,
    ) -> np.ndarray:
        """
        PNG/JPEG/WebPおよび
        Windows日本語パス対応の画像読込。
        """

        if not image_path.exists():
            raise FileNotFoundError(
                f"画像が存在しません: {image_path}"
            )

        data = np.fromfile(
            str(image_path),
            dtype=np.uint8,
        )

        if data.size == 0:
            raise RuntimeError(
                f"画像データが空です: {image_path}"
            )

        image = cv2.imdecode(
            data,
            cv2.IMREAD_COLOR,
        )

        if image is None:
            raise RuntimeError(
                f"画像を読み込めません: {image_path}"
            )

        return image

    def _find_label_index(
        self,
        texts: list[str],
        label: str,
    ) -> int | None:
        normalized_label = (
            self._normalize_label(
                label
            )
        )

        for index, text in enumerate(texts):
            if (
                self._normalize_label(
                    text
                )
                == normalized_label
            ):
                return index

        return None

    def _normalize_label(
        self,
        text: str,
    ) -> str:
        return re.sub(
            r"[^A-Z]",
            "",
            text.upper(),
        )

    def _digits_only(
        self,
        text: str,
    ) -> str:
        """文字列から数字だけを取り出す。"""

        return re.sub(
            r"\D",
            "",
            text,
        )

    def _get_box(
        self,
        boxes,
        index: int,
    ):
        if boxes is None:
            return None

        if index < 0:
            return None

        if index >= len(boxes):
            return None

        box = boxes[index]

        if box is None:
            return None

        if len(box) < 4:
            return None

        return box

    def _box_center_x(
        self,
        box,
    ) -> float:
        return (
            float(box[0])
            + float(box[2])
        ) / 2.0

    def _box_center_y(
        self,
        box,
    ) -> float:
        return (
            float(box[1])
            + float(box[3])
        ) / 2.0