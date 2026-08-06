from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class CharacterCandidate:
    """キャラ候補。"""

    name: str
    score: float


@dataclass(frozen=True)
class CharacterRecognitionResult:
    """キャラ認識結果。"""

    character_name: str | None
    confidence: float
    candidates: list[CharacterCandidate]


class CharacterRecognizer:
    """SIFT特徴量を使ってキャラ画像を判定する。"""

    IMAGE_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    }

    MIN_CONFIDENCE = 0.20

    # 1位と2位が近すぎる場合は誤判定を避ける。
    MIN_MARGIN = 0.04

    def __init__(
        self,
        template_dir: Path,
    ) -> None:
        self.template_dir = template_dir

        self.sift = cv2.SIFT_create(
            nfeatures=600
        )

        self.matcher = cv2.BFMatcher(
            cv2.NORM_L2
        )

    def recognize(
        self,
        image: np.ndarray,
    ) -> CharacterRecognitionResult:
        """1枚のキャラ画像を判定する。"""

        target = self._prepare_image(
            image
        )

        target_keypoints, target_descriptors = (
            self.sift.detectAndCompute(
                target,
                None,
            )
        )

        if (
            target_descriptors is None
            or len(target_keypoints) < 5
        ):
            return CharacterRecognitionResult(
                character_name=None,
                confidence=0.0,
                candidates=[],
            )

        scores: dict[str, float] = {}

        for character_dir in (
            self._character_directories()
        ):
            character_name = (
                character_dir.name
            )

            best_score = 0.0

            for template_path in (
                self._template_images(
                    character_dir
                )
            ):
                score = self._compare(
                    target_keypoints=target_keypoints,
                    target_descriptors=(
                        target_descriptors
                    ),
                    template_path=template_path,
                )

                best_score = max(
                    best_score,
                    score,
                )

            scores[character_name] = (
                best_score
            )

        candidates = [
            CharacterCandidate(
                name=name,
                score=score,
            )
            for name, score in sorted(
                scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

        if not candidates:
            return CharacterRecognitionResult(
                character_name=None,
                confidence=0.0,
                candidates=[],
            )

        best = candidates[0]

        second_score = (
            candidates[1].score
            if len(candidates) >= 2
            else 0.0
        )

        margin = (
            best.score - second_score
        )

        if (
            best.score < self.MIN_CONFIDENCE
            or margin < self.MIN_MARGIN
        ):
            return CharacterRecognitionResult(
                character_name=None,
                confidence=best.score,
                candidates=candidates[:3],
            )

        return CharacterRecognitionResult(
            character_name=best.name,
            confidence=best.score,
            candidates=candidates[:3],
        )

    def _compare(
        self,
        target_keypoints: list,
        target_descriptors: np.ndarray,
        template_path: Path,
    ) -> float:
        """対象画像とテンプレートを比較する。"""

        template = self._read_image(
            template_path
        )

        if template is None:
            return 0.0

        template = self._prepare_image(
            template
        )

        (
            template_keypoints,
            template_descriptors,
        ) = self.sift.detectAndCompute(
            template,
            None,
        )

        if (
            template_descriptors is None
            or len(template_keypoints) < 5
        ):
            return 0.0

        matches = self.matcher.knnMatch(
            target_descriptors,
            template_descriptors,
            k=2,
        )

        good_matches = []

        for match_pair in matches:
            if len(match_pair) < 2:
                continue

            first, second = match_pair

            if first.distance < (
                0.72 * second.distance
            ):
                good_matches.append(
                    first
                )

        denominator = max(
            1,
            min(
                len(target_keypoints),
                len(template_keypoints),
            ),
        )

        return min(
            len(good_matches)
            / denominator,
            1.0,
        )

    def _prepare_image(
        self,
        image: np.ndarray,
    ) -> np.ndarray:
        """比較しやすい画像へ正規化する。"""

        resized = cv2.resize(
            image,
            (256, 256),
            interpolation=cv2.INTER_AREA,
        )

        gray = cv2.cvtColor(
            resized,
            cv2.COLOR_BGR2GRAY,
        )

        # UI枠の影響を少し減らすため、
        # 外周を切り落とす。
        height, width = gray.shape

        x1 = int(
            width * 0.05
        )
        x2 = int(
            width * 0.95
        )

        y1 = int(
            height * 0.03
        )
        y2 = int(
            height * 0.92
        )

        return gray[
            y1:y2,
            x1:x2,
        ]

    def _character_directories(
        self,
    ) -> list[Path]:
        if not self.template_dir.exists():
            return []

        return [
            path
            for path in self.template_dir.iterdir()
            if path.is_dir()
        ]

    def _template_images(
        self,
        character_dir: Path,
    ) -> list[Path]:
        return [
            path
            for path in character_dir.iterdir()
            if (
                path.is_file()
                and path.suffix.lower()
                in self.IMAGE_EXTENSIONS
            )
        ]
    
    def _read_image(
        self,
        image_path: Path,
    ) -> np.ndarray | None:
        """日本語を含むWindowsパスから画像を読み込む。"""

        try:
            data = np.fromfile(
                str(image_path),
                dtype=np.uint8,
            )

            if data.size == 0:
                return None

            return cv2.imdecode(
                data,
                cv2.IMREAD_COLOR,
            )

        except Exception:
            return None