from dataclasses import dataclass
import re


@dataclass(frozen=True)
class BattleOcrResult:
    """戦闘結果画面から抽出した情報。"""

    boss_name: str | None
    boss_name_confidence: float | None

    boss_max_hp: int | None
    boss_max_hp_confidence: float | None

    total_damage: int | None
    total_damage_confidence: float | None


class BattleResultParser:
    """PaddleOCRの結果から戦闘情報を抽出する。"""

    def parse(
        self,
        texts: list[str],
        scores: list[float],
        known_boss_names: list[str],
    ) -> BattleOcrResult:
        """OCR結果からBoss・最大HP・Damageを抽出する。"""

        (
            boss_name,
            boss_name_confidence,
        ) = self._find_boss_name(
            texts=texts,
            scores=scores,
            known_boss_names=known_boss_names,
        )

        (
            boss_max_hp,
            boss_max_hp_confidence,
        ) = self._find_boss_max_hp(
            texts=texts,
            scores=scores,
        )

        (
            total_damage,
            total_damage_confidence,
        ) = self._find_value_after_label(
            texts=texts,
            scores=scores,
            label="TOTALDAMAGE",
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
        """登録済みBoss名と一致するOCR文字列を探す。"""

        normalized_boss_names = {
            self._normalize_text(name): name
            for name in known_boss_names
        }

        for index, text in enumerate(texts):
            normalized_text = self._normalize_text(
                text
            )

            boss_name = normalized_boss_names.get(
                normalized_text
            )

            if boss_name is None:
                continue

            confidence = (
                float(scores[index])
                if index < len(scores)
                else None
            )

            return boss_name, confidence

        return None, None

    def _find_boss_max_hp(
        self,
        texts: list[str],
        scores: list[float],
    ) -> tuple[int | None, float | None]:
        """
        HP REMAININGの後ろにある2番目の数値を
        Boss最大HPとして取得する。

        例:
            HP REMAINING
            13,423,147,627   ← 残HP（使用しない）
            149,784,418,800  ← 最大HP
        """

        label_index = self._find_label_index(
            texts=texts,
            label="HPREMAINING",
        )

        if label_index is None:
            return None, None

        found_numbers: list[
            tuple[int, float | None]
        ] = []

        search_end = min(
            label_index + 5,
            len(texts),
        )

        for index in range(
            label_index + 1,
            search_end,
        ):
            value = self._parse_number(
                texts[index]
            )

            if value is None:
                continue

            confidence = (
                float(scores[index])
                if index < len(scores)
                else None
            )

            found_numbers.append(
                (
                    value,
                    confidence,
                )
            )

        if len(found_numbers) < 2:
            return None, None

        return found_numbers[1]

    def _find_value_after_label(
        self,
        texts: list[str],
        scores: list[float],
        label: str,
    ) -> tuple[int | None, float | None]:
        """ラベル直後の数値を取得する。"""

        label_index = self._find_label_index(
            texts=texts,
            label=label,
        )

        if label_index is None:
            return None, None

        search_end = min(
            label_index + 4,
            len(texts),
        )

        for index in range(
            label_index + 1,
            search_end,
        ):
            value = self._parse_number(
                texts[index]
            )

            if value is None:
                continue

            confidence = (
                float(scores[index])
                if index < len(scores)
                else None
            )

            return value, confidence

        return None, None

    def _find_label_index(
        self,
        texts: list[str],
        label: str,
    ) -> int | None:
        """指定ラベルの位置を検索する。"""

        for index, text in enumerate(texts):
            if self._normalize_label(text) == label:
                return index

        return None

    def _parse_number(
        self,
        text: str,
    ) -> int | None:
        """数値文字列をintへ変換する。"""

        normalized = text.strip()

        if not re.fullmatch(
            r"\d{1,3}(?:,\d{3})*|\d+",
            normalized,
        ):
            return None

        return int(
            normalized.replace(",", "")
        )

    def _normalize_label(
        self,
        text: str,
    ) -> str:
        """英字ラベル比較用。"""

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