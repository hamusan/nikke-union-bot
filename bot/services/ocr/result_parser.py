from dataclasses import dataclass
import re


@dataclass(frozen=True)
class BattleOcrResult:
    """戦闘結果OCRの解析結果。"""

    boss_name: str | None
    boss_name_confidence: float | None

    boss_max_hp: int | None
    boss_max_hp_confidence: float | None

    total_damage: int | None
    total_damage_confidence: float | None


class BattleResultParser:
    """PaddleOCRの結果から戦闘情報を解析する。"""

    def parse(
        self,
        texts: list[str],
        scores: list[float],
        boxes,
        known_boss_names: list[str],
    ) -> BattleOcrResult:
        """OCR結果からBoss・最大HP・Damageを取得する。"""

        boss_name, boss_name_confidence = (
            self._find_boss_name(
                texts=texts,
                scores=scores,
                known_boss_names=known_boss_names,
            )
        )

        boss_max_hp, boss_max_hp_confidence = (
            self._find_boss_max_hp(
                texts=texts,
                scores=scores,
                boxes=boxes,
            )
        )

        total_damage, total_damage_confidence = (
            self._find_total_damage(
                texts=texts,
                scores=scores,
                boxes=boxes,
            )
        )

        return BattleOcrResult(
            boss_name=boss_name,
            boss_name_confidence=boss_name_confidence,
            boss_max_hp=boss_max_hp,
            boss_max_hp_confidence=boss_max_hp_confidence,
            total_damage=total_damage,
            total_damage_confidence=total_damage_confidence,
        )

    def _find_boss_name(
        self,
        texts: list[str],
        scores: list[float],
        known_boss_names: list[str],
    ) -> tuple[str | None, float | None]:
        """登録済みBoss名とOCR文字列を照合する。"""

        normalized_bosses = {
            self._normalize_text(name): name
            for name in known_boss_names
        }

        for index, text in enumerate(texts):
            normalized = self._normalize_text(
                text
            )

            boss_name = normalized_bosses.get(
                normalized
            )

            if boss_name is None:
                continue

            return (
                boss_name,
                self._get_score(
                    scores,
                    index,
                ),
            )

        return None, None

    def _find_boss_max_hp(
        self,
        texts: list[str],
        scores: list[float],
        boxes,
    ) -> tuple[int | None, float | None]:
        """
        HP Remaining と TOTAL DAMAGE の
        画面上の間にあるHP表示を解析する。

        NIKKEでは、

            残HP / 最大HP

        と表示されるため、

        1. "/" または "／" から始まる数値を最優先
        2. "/" が認識されなかった場合は最大値

        というルールで最大HPを判定する。
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
            return None, None

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
            return self._find_boss_max_hp_fallback(
                texts=texts,
                scores=scores,
            )

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

        slash_candidates: list[
            tuple[int, float | None]
        ] = []

        normal_candidates: list[
            tuple[int, float | None]
        ] = []

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

            # HP Remaining と TOTAL DAMAGE の
            # 画面上の間だけを見る。
            if not (
                top_y < center_y < bottom_y
            ):
                continue

            values = self._extract_numbers(
                text
            )

            if not values:
                continue

            stripped = text.strip()

            starts_with_slash = (
                stripped.startswith("/")
                or stripped.startswith("／")
            )

            for value in values:
                candidate = (
                    value,
                    self._get_score(
                        scores,
                        index,
                    ),
                )

                if starts_with_slash:
                    slash_candidates.append(
                        candidate
                    )
                else:
                    normal_candidates.append(
                        candidate
                    )

        # "/最大HP" が認識されているなら
        # 数字の大小に関係なく最大HPとして採用する。
        if slash_candidates:
            return slash_candidates[0]

        # "/" がOCRされなかった場合だけ、
        # HP候補の最大値を使う。
        if normal_candidates:
            return max(
                normal_candidates,
                key=lambda item: item[0],
            )

        return None, None

    def _find_total_damage(
        self,
        texts: list[str],
        scores: list[float],
        boxes,
    ) -> tuple[int | None, float | None]:
        """
        TOTAL DAMAGE の画面上で
        最も近い下側の数値をDamageとする。
        """

        label_index = self._find_label_index(
            texts=texts,
            label="TOTALDAMAGE",
        )

        if label_index is None:
            return None, None

        label_box = self._get_box(
            boxes,
            label_index,
        )

        if label_box is None:
            return self._find_total_damage_fallback(
                texts=texts,
                scores=scores,
            )

        label_y = self._box_center_y(
            label_box
        )

        candidates: list[
            tuple[float, int, float | None]
        ] = []

        for index, text in enumerate(texts):
            if index == label_index:
                continue

            box = self._get_box(
                boxes,
                index,
            )

            if box is None:
                continue

            center_y = self._box_center_y(
                box
            )

            # TOTAL DAMAGEより上側は無視。
            if center_y <= label_y:
                continue

            values = self._extract_numbers(
                text
            )

            if not values:
                continue

            distance = (
                center_y - label_y
            )

            for value in values:
                candidates.append(
                    (
                        distance,
                        value,
                        self._get_score(
                            scores,
                            index,
                        ),
                    )
                )

        if not candidates:
            return None, None

        # TOTAL DAMAGEに最も近い下側の数値。
        _, value, confidence = min(
            candidates,
            key=lambda item: item[0],
        )

        return (
            value,
            confidence,
        )

    def _find_boss_max_hp_fallback(
        self,
        texts: list[str],
        scores: list[float],
    ) -> tuple[int | None, float | None]:
        """
        rec_boxesが利用できない場合の
        フォールバック処理。
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
            return None, None

        start = min(
            hp_index,
            damage_index,
        ) + 1

        end = max(
            hp_index,
            damage_index,
        )

        slash_candidates: list[
            tuple[int, float | None]
        ] = []

        normal_candidates: list[
            tuple[int, float | None]
        ] = []

        for index in range(
            start,
            end,
        ):
            text = texts[index]

            values = self._extract_numbers(
                text
            )

            if not values:
                continue

            stripped = text.strip()

            starts_with_slash = (
                stripped.startswith("/")
                or stripped.startswith("／")
            )

            for value in values:
                candidate = (
                    value,
                    self._get_score(
                        scores,
                        index,
                    ),
                )

                if starts_with_slash:
                    slash_candidates.append(
                        candidate
                    )
                else:
                    normal_candidates.append(
                        candidate
                    )

        if slash_candidates:
            return slash_candidates[0]

        if normal_candidates:
            return max(
                normal_candidates,
                key=lambda item: item[0],
            )

        return None, None

    def _find_total_damage_fallback(
        self,
        texts: list[str],
        scores: list[float],
    ) -> tuple[int | None, float | None]:
        """座標が無い場合のDamage判定。"""

        label_index = self._find_label_index(
            texts=texts,
            label="TOTALDAMAGE",
        )

        if label_index is None:
            return None, None

        end_index = min(
            len(texts),
            label_index + 6,
        )

        for index in range(
            label_index + 1,
            end_index,
        ):
            values = self._extract_numbers(
                texts[index]
            )

            if not values:
                continue

            return (
                values[0],
                self._get_score(
                    scores,
                    index,
                ),
            )

        return None, None

    def _extract_numbers(
        self,
        text: str,
    ) -> list[int]:
        """
        OCR文字列内の整数をすべて取得する。

        例:

        "131,480,369,448"
        -> [131480369448]

        "/150,841,81,600"
        -> [15084181600]

        "131,480,369,448 / 150,841,811,600"
        -> [
            131480369448,
            150841811600,
        ]
        """

        matches = re.findall(
            r"\d{1,3}(?:,\d{1,3})+|\d+",
            text,
        )

        values: list[int] = []

        for match in matches:
            digits = match.replace(
                ",",
                "",
            )

            if not digits.isdigit():
                continue

            try:
                values.append(
                    int(digits)
                )

            except ValueError:
                continue

        return values

    def _find_label_index(
        self,
        texts: list[str],
        label: str,
    ) -> int | None:
        """指定ラベルのOCRインデックスを取得する。"""

        normalized_label = self._normalize_label(
            label
        )

        for index, text in enumerate(texts):
            normalized = self._normalize_label(
                text
            )

            if normalized == normalized_label:
                return index

        return None

    def _get_box(
        self,
        boxes,
        index: int,
    ):
        """OCR boxを安全に取得する。"""

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

    def _box_center_y(
        self,
        box,
    ) -> float:
        """
        rec_boxes形式:
        [x1, y1, x2, y2]

        の中央Y座標を取得する。
        """

        return (
            float(box[1])
            + float(box[3])
        ) / 2.0

    def _normalize_label(
        self,
        text: str,
    ) -> str:
        """
        ラベル比較用。

        HP Remaining
        HPREMAINING

        TOTAL DAMAGE
        TOTALDAMAGE

        を同じものとして扱う。
        """

        return re.sub(
            r"[^A-Z]",
            "",
            text.upper(),
        )

    def _normalize_text(
        self,
        text: str,
    ) -> str:
        """Boss名比較用。"""

        return re.sub(
            r"\s+",
            "",
            text,
        ).casefold()

    def _get_score(
        self,
        scores: list[float],
        index: int,
    ) -> float | None:
        """OCR confidenceを安全に取得する。"""

        if index < 0:
            return None

        if index >= len(scores):
            return None

        return float(
            scores[index]
        )