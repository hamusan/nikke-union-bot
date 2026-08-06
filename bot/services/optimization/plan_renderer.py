from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
)

from bot.services.optimization.assignment import (
    BossAssignmentSummary,
    UnionAssignmentPlan,
)
from bot.services.optimization.character_icon_loader import (
    CharacterIconLoader,
)


class OptimizationPlanImageRenderer:
    """
    最適化結果をPNG画像へ変換する。

    使用キャラは文字ではなく
    画像アイコンで描画する。
    """

    WIDTH = 1600

    OUTER_MARGIN = 60
    CARD_GAP = 28

    ICON_SIZE = 250
    ICON_GAP = 32

    BACKGROUND = "#101218"
    CARD_BACKGROUND = "#1b1f2a"
    CARD_BORDER = "#343b4d"

    TEXT_MAIN = "#f3f4f6"
    TEXT_SUB = "#aeb5c4"
    TEXT_ACCENT = "#ffffff"
    PLACEHOLDER_BG = "#222838"
    PLACEHOLDER_BORDER = "#4f5b78"

    def __init__(
        self,
        font_path: str | Path | None = None,
    ) -> None:
        self._font_path = (
            Path(font_path)
            if font_path is not None
            else None
        )

        self.icon_loader = (
            CharacterIconLoader(
                icon_size=self.ICON_SIZE
            )
        )

    def render(
        self,
        plan: UnionAssignmentPlan,
        raid_name: str,
    ) -> bytes:
        """最適化プランをPNG bytesとして生成する。"""

        title_font = self._load_font(
            64,
            bold=True,
        )

        raid_font = self._load_font(
            38,
            bold=True,
        )

        boss_font = self._load_font(
            60,
            bold=True,
        )

        normal_font = self._load_font(
            25,
        )

        small_font = self._load_font(
            21,
        )

        dummy_image = Image.new(
            "RGB",
            (1, 1),
        )

        dummy_draw = ImageDraw.Draw(
            dummy_image
        )

        card_heights = [
            self._calculate_card_height(
                draw=dummy_draw,
                boss=boss,
                small_font=small_font,
            )
            for boss in plan.boss_summaries
        ]

        header_height = 260

        if card_heights:
            total_height = (
                header_height
                + sum(card_heights)
                + self.CARD_GAP
                * (len(card_heights) - 1)
                + self.OUTER_MARGIN
            )
        else:
            total_height = 500

        image = Image.new(
            "RGB",
            (
                self.WIDTH,
                total_height,
            ),
            self.BACKGROUND,
        )

        draw = ImageDraw.Draw(
            image
        )

        # ================================================
        # Header
        # ================================================

        x = self.OUTER_MARGIN
        y = 48

        draw.text(
            (x, y),
            "ユニオンレイド 最適化プラン",
            font=title_font,
            fill=self.TEXT_MAIN,
        )

        y += 76

        draw.text(
            (x, y),
            f"Raid: {raid_name}",
            font=raid_font,
            fill=self.TEXT_ACCENT,
        )

        y += 52

        summary = (
            f"割り当て {plan.attack_count}凸"
            f"   |   合計Damage "
            f"{plan.total_nominal_damage:,}"
            f"   |   有効Damage "
            f"{plan.total_effective_damage:,}"
        )

        draw.text(
            (x, y),
            summary,
            font=normal_font,
            fill=self.TEXT_SUB,
        )

        y += 42

        draw.text(
            (x, y),
            "※ 攻撃順序は考慮していません",
            font=small_font,
            fill=self.TEXT_SUB,
        )

        # ================================================
        # Boss cards
        # ================================================

        card_y = header_height

        if not plan.boss_summaries:
            draw.text(
                (
                    self.OUTER_MARGIN,
                    card_y,
                ),
                "現在、割り当て可能な攻撃がありません。",
                font=normal_font,
                fill=self.TEXT_SUB,
            )

        for (
            boss,
            card_height,
        ) in zip(
            plan.boss_summaries,
            card_heights,
            strict=True,
        ):
            self._draw_boss_card(
                image=image,
                draw=draw,
                boss=boss,
                top=card_y,
                height=card_height,
                boss_font=boss_font,
                normal_font=normal_font,
                small_font=small_font,
            )

            card_y += (
                card_height
                + self.CARD_GAP
            )

        output = BytesIO()

        image.save(
            output,
            format="PNG",
            optimize=True,
        )

        return output.getvalue()

    def _calculate_card_height(
        self,
        draw: ImageDraw.ImageDraw,
        boss: BossAssignmentSummary,
        small_font: ImageFont.FreeTypeFont,
    ) -> int:
        """Bossカードに必要な高さを計算する。"""

        height = 150

        max_text_width = (
            self.WIDTH
            - self.OUTER_MARGIN * 4
        )

        for assignment in boss.assignments:
            # 上段テキスト
            height += 42

            # アイコン行
            height += (
                self.ICON_SIZE + 14
            )

            missing_names = [
                name
                for name in assignment.character_names
                if not self.icon_loader.has_icon(
                    name
                )
            ]

            if missing_names:
                missing_text = (
                    "未登録: "
                    + " / ".join(
                        missing_names
                    )
                )

                wrapped = self._wrap_text(
                    draw=draw,
                    text=missing_text,
                    font=small_font,
                    max_width=max_text_width,
                )

                height += (
                    len(wrapped)
                    * 28
                )

            height += 18

        height += 30

        return max(
            height,
            220,
        )

    def _draw_boss_card(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        boss: BossAssignmentSummary,
        top: int,
        height: int,
        boss_font: ImageFont.FreeTypeFont,
        normal_font: ImageFont.FreeTypeFont,
        small_font: ImageFont.FreeTypeFont,
    ) -> None:
        """Boss 1体分を描画する。"""

        left = self.OUTER_MARGIN
        right = (
            self.WIDTH
            - self.OUTER_MARGIN
        )

        bottom = top + height

        draw.rounded_rectangle(
            (
                left,
                top,
                right,
                bottom,
            ),
            radius=24,
            fill=self.CARD_BACKGROUND,
            outline=self.CARD_BORDER,
            width=2,
        )

        x = left + 32
        y = top + 28

        draw.text(
            (x, y),
            (
                f"{boss.boss_name}"
                f"   |   Phase {boss.phase_no}"
            ),
            font=boss_font,
            fill=self.TEXT_MAIN,
        )

        y += 76

        stats = (
            f"HP {boss.max_hp:,}"
            f"   |   割り当て "
            f"{boss.assigned_damage:,}"
            f"   |   Overkill "
            f"{boss.overkill_damage:,}"
        )

        draw.text(
            (x, y),
            stats,
            font=small_font,
            fill=self.TEXT_SUB,
        )

        y += 38

        max_text_width = (
            right
            - x
            - 36
        )

        for assignment in boss.assignments:
            attack_text = (
                f"{assignment.player_name}"
                f"   /   Team #{assignment.team_no}"
                f"   /   {assignment.damage:,}"
            )

            draw.text(
                (x, y),
                attack_text,
                font=normal_font,
                fill=self.TEXT_MAIN,
            )

            y += 42

            icon_x = x
            missing_names: list[str] = []

            for character_name in (
                assignment.character_names
            ):
                icon = self.icon_loader.get_icon(
                    character_name
                )

                if icon is not None:
                    image.paste(
                        icon,
                        (
                            icon_x,
                            y,
                        ),
                        icon,
                    )
                else:
                    self._draw_placeholder_icon(
                        draw=draw,
                        x=icon_x,
                        y=y,
                        label="?",
                        font=small_font,
                    )

                    missing_names.append(
                        character_name
                    )

                icon_x += (
                    self.ICON_SIZE
                    + self.ICON_GAP
                )

            y += (
                self.ICON_SIZE + 12
            )

            if missing_names:
                missing_text = (
                    "未登録: "
                    + " / ".join(
                        missing_names
                    )
                )

                wrapped = self._wrap_text(
                    draw=draw,
                    text=missing_text,
                    font=small_font,
                    max_width=max_text_width,
                )

                for line in wrapped:
                    draw.text(
                        (x, y),
                        line,
                        font=small_font,
                        fill=self.TEXT_SUB,
                    )

                    y += 28

            y += 18

    def _draw_placeholder_icon(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        label: str,
        font: ImageFont.FreeTypeFont,
    ) -> None:
        """画像が無いキャラ用のプレースホルダー。"""

        draw.rounded_rectangle(
            (
                x,
                y,
                x + self.ICON_SIZE,
                y + self.ICON_SIZE,
            ),
            radius=12,
            fill=self.PLACEHOLDER_BG,
            outline=self.PLACEHOLDER_BORDER,
            width=2,
        )

        bbox = draw.textbbox(
            (0, 0),
            label,
            font=font,
        )

        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        tx = x + (
            self.ICON_SIZE - text_w
        ) // 2

        ty = y + (
            self.ICON_SIZE - text_h
        ) // 2 - 1

        draw.text(
            (tx, ty),
            label,
            font=font,
            fill=self.TEXT_MAIN,
        )

    def _wrap_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
    ) -> list[str]:
        """
        日本語でも使えるように、
        文字単位で折り返す。
        """

        if not text:
            return []

        result: list[str] = []
        current = ""

        for char in text:
            candidate = (
                current + char
            )

            bbox = draw.textbbox(
                (0, 0),
                candidate,
                font=font,
            )

            width = (
                bbox[2]
                - bbox[0]
            )

            if (
                current
                and width > max_width
            ):
                result.append(
                    current
                )
                current = char
            else:
                current = candidate

        if current:
            result.append(
                current
            )

        return result

    def _load_font(
        self,
        size: int,
        bold: bool = False,
    ) -> ImageFont.FreeTypeFont:
        """
        日本語フォントを探して読み込む。
        """

        if self._font_path is not None:
            return ImageFont.truetype(
                str(self._font_path),
                size=size,
            )

        if bold:
            candidates = (
                Path(
                    r"C:\Windows\Fonts\YuGothB.ttc"
                ),
                Path(
                    r"C:\Windows\Fonts\meiryob.ttc"
                ),
                Path(
                    "/usr/share/fonts/opentype/noto/"
                    "NotoSansCJK-Bold.ttc"
                ),
            )
        else:
            candidates = (
                Path(
                    r"C:\Windows\Fonts\YuGothM.ttc"
                ),
                Path(
                    r"C:\Windows\Fonts\meiryo.ttc"
                ),
                Path(
                    "/usr/share/fonts/opentype/noto/"
                    "NotoSansCJK-Regular.ttc"
                ),
            )

        for path in candidates:
            if not path.exists():
                continue

            return ImageFont.truetype(
                str(path),
                size=size,
            )

        raise RuntimeError(
            (
                "日本語フォントが見つかりません。"
                "WindowsではYu GothicまたはMeiryo、"
                "UbuntuではNoto Sans CJKを"
                "インストールしてください。"
            )
        )