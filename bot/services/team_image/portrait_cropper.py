from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class PortraitCropResult:
    """キャラ画像切り出し結果。"""

    panel_box: tuple[int, int, int, int]
    portraits: list[np.ndarray]


class PortraitDetectionError(Exception):
    """戦闘履歴パネルを検出できなかった場合。"""


class TeamPortraitCropper:
    """戦闘履歴画面から5人分のキャラ画像を切り出す。"""

    PORTRAIT_COUNT = 5

    # 戦闘履歴の白いパネル内部における
    # キャラ画像の相対位置。
    PORTRAIT_X = 0.050
    PORTRAIT_WIDTH = 0.225

    FIRST_PORTRAIT_Y = 0.080
    PORTRAIT_HEIGHT = 0.175

    ROW_STEP = 0.1775

    NORMALIZED_SIZE = 160

    def crop(
        self,
        image_path: Path,
    ) -> PortraitCropResult:
        """画像から5人分のキャラ画像を取得する。"""

        image = cv2.imread(
            str(image_path)
        )

        if image is None:
            raise RuntimeError(
                f"画像を読み込めません: {image_path}"
            )

        panel_box = self._detect_panel(
            image
        )

        x, y, width, height = panel_box

        panel = image[
            y:y + height,
            x:x + width,
        ]

        portraits: list[np.ndarray] = []

        for index in range(
            self.PORTRAIT_COUNT
        ):
            portrait = self._crop_portrait(
                panel=panel,
                index=index,
            )

            portraits.append(
                portrait
            )

        return PortraitCropResult(
            panel_box=panel_box,
            portraits=portraits,
        )

    def _detect_panel(
        self,
        image: np.ndarray,
    ) -> tuple[int, int, int, int]:
        """
        白～薄いグレーの戦闘履歴パネルを検出する。

        スクリーンショット全体の位置・解像度には
        依存しない。
        """

        hsv = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2HSV,
        )

        # 白～薄いグレーを抽出。
        lower = np.array(
            [0, 0, 175],
            dtype=np.uint8,
        )

        upper = np.array(
            [180, 90, 255],
            dtype=np.uint8,
        )

        mask = cv2.inRange(
            hsv,
            lower,
            upper,
        )

        # 細かい文字などをつなげて
        # 大きなパネル領域として扱いやすくする。
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (7, 7),
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_CLOSE,
            kernel,
        )

        count, _, stats, _ = (
            cv2.connectedComponentsWithStats(
                mask
            )
        )

        image_height, image_width = (
            image.shape[:2]
        )

        image_area = (
            image_width * image_height
        )

        candidates: list[
            tuple[int, int, int, int, int]
        ] = []

        for label in range(
            1,
            count,
        ):
            x = int(
                stats[
                    label,
                    cv2.CC_STAT_LEFT,
                ]
            )

            y = int(
                stats[
                    label,
                    cv2.CC_STAT_TOP,
                ]
            )

            width = int(
                stats[
                    label,
                    cv2.CC_STAT_WIDTH,
                ]
            )

            height = int(
                stats[
                    label,
                    cv2.CC_STAT_HEIGHT,
                ]
            )

            area = int(
                stats[
                    label,
                    cv2.CC_STAT_AREA,
                ]
            )

            if height <= 0:
                continue

            aspect_ratio = (
                width / height
            )

            area_ratio = (
                area / image_area
            )

            # 今回の3画像では
            # パネル比率 ≒ 0.767。
            #
            # スマホ等を考慮して
            # かなり余裕を持たせる。
            if not (
                0.65
                <= aspect_ratio
                <= 0.90
            ):
                continue

            # 小さな白UIを除外。
            if area_ratio < 0.05:
                continue

            candidates.append(
                (
                    area,
                    x,
                    y,
                    width,
                    height,
                )
            )

        if not candidates:
            raise PortraitDetectionError(
                "戦闘履歴パネルを検出できませんでした。"
            )

        # 最も大きい候補を使用。
        _, x, y, width, height = max(
            candidates,
            key=lambda candidate: candidate[0],
        )

        return (
            x,
            y,
            width,
            height,
        )

    def _crop_portrait(
        self,
        panel: np.ndarray,
        index: int,
    ) -> np.ndarray:
        """パネル内の相対座標からキャラ画像を取得する。"""

        panel_height, panel_width = (
            panel.shape[:2]
        )

        relative_y = (
            self.FIRST_PORTRAIT_Y
            + self.ROW_STEP * index
        )

        x1 = int(
            panel_width
            * self.PORTRAIT_X
        )

        y1 = int(
            panel_height
            * relative_y
        )

        x2 = int(
            panel_width
            * (
                self.PORTRAIT_X
                + self.PORTRAIT_WIDTH
            )
        )

        y2 = int(
            panel_height
            * (
                relative_y
                + self.PORTRAIT_HEIGHT
            )
        )

        # 画像外にはみ出さないようにする。
        x1 = max(
            0,
            x1,
        )

        y1 = max(
            0,
            y1,
        )

        x2 = min(
            panel_width,
            x2,
        )

        y2 = min(
            panel_height,
            y2,
        )

        crop = panel[
            y1:y2,
            x1:x2,
        ]

        if crop.size == 0:
            raise PortraitDetectionError(
                f"キャラ {index + 1} の"
                "切り出しに失敗しました。"
            )

        # 全画像を同じサイズへ。
        normalized = cv2.resize(
            crop,
            (
                self.NORMALIZED_SIZE,
                self.NORMALIZED_SIZE,
            ),
            interpolation=cv2.INTER_AREA,
        )

        return normalized