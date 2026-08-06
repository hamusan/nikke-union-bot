from __future__ import annotations

from pathlib import Path

from PIL import (
    Image,
    ImageDraw,
    ImageOps,
)

from bot.data.character_icon_map import (
    resolve_character_icon_path,
)


class CharacterIconLoader:
    """
    使用キャラ画像を読み込む。

    優先順位:
    1. assets/character_icons の表示用アイコン
    2. uploads/character_templates/<キャラ名>/pc_1.png
    3. 見つからなければ None
    """

    def __init__(
        self,
        icon_size: int = 56,
        template_base_dir: str | Path = (
            "uploads/character_templates"
        ),
    ) -> None:
        self.icon_size = icon_size
        self.template_base_dir = Path(
            template_base_dir
        )

        self._cache: dict[
            str,
            Image.Image | None,
        ] = {}

    def get_icon(
        self,
        character_name: str,
    ) -> Image.Image | None:
        """
        キャラ画像を取得する。
        なければNone。
        """

        if character_name in self._cache:
            cached = self._cache[
                character_name
            ]

            if cached is None:
                return None

            return cached.copy()

        source_path = self._resolve_source_path(
            character_name
        )

        if source_path is None:
            self._cache[
                character_name
            ] = None
            return None

        try:
            icon = self._load_and_prepare_icon(
                source_path
            )
        except Exception:
            self._cache[
                character_name
            ] = None
            return None

        self._cache[
            character_name
        ] = icon

        return icon.copy()

    def has_icon(
        self,
        character_name: str,
    ) -> bool:
        return (
            self.get_icon(character_name)
            is not None
        )

    def _resolve_source_path(
        self,
        character_name: str,
    ) -> Path | None:
        """
        表示用アイコン → OCRテンプレート の順で探索する。
        """

        display_icon = resolve_character_icon_path(
            character_name
        )

        if (
            display_icon is not None
            and display_icon.exists()
        ):
            return display_icon

        fallback_template = (
            self.template_base_dir
            / character_name
            / "pc_1.png"
        )

        if fallback_template.exists():
            return fallback_template

        return None

    def _load_and_prepare_icon(
        self,
        source_path: Path,
    ) -> Image.Image:
        """
        画像を読み込み、表示用の正方形アイコンへ整形する。
        """

        source = Image.open(
            source_path
        ).convert("RGBA")

        content_size = (
            self.icon_size - 10,
            self.icon_size - 10,
        )

        resized = ImageOps.contain(
            source,
            content_size,
            Image.LANCZOS,
        )

        canvas = Image.new(
            "RGBA",
            (
                self.icon_size,
                self.icon_size,
            ),
            (0, 0, 0, 0),
        )

        draw = ImageDraw.Draw(
            canvas
        )

        draw.rounded_rectangle(
            (
                0,
                0,
                self.icon_size - 1,
                self.icon_size - 1,
            ),
            radius=12,
            fill="#11151e",
            outline="#4a5266",
            width=2,
        )

        x = (
            self.icon_size
            - resized.width
        ) // 2

        y = (
            self.icon_size
            - resized.height
        ) // 2

        canvas.alpha_composite(
            resized,
            (x, y),
        )

        return canvas