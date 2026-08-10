from __future__ import annotations

from io import BytesIO
from pathlib import Path

from dataclasses import dataclass
from datetime import datetime
import re

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

@dataclass(frozen=True)
class RenderedBossImage:
    filename: str
    boss_name: str
    png_bytes: bytes

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
        """最適化プラン画像をPNG bytesとして生成する。"""

        title_font = self._load_font(
            64,
            bold=True,
        )

        raid_font = self._load_font(
            38,
            bold=True,
        )

        phase_font = self._load_font(
            34,
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

        header_height = 310

        if card_heights:
            total_height = (
                header_height
                + sum(card_heights)
                + self.CARD_GAP
                * (len(card_heights) - 1)
                + self.OUTER_MARGIN
            )
        else:
            total_height = 560

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

        current_phase_text = self._resolve_phase_text(
            plan
        )

        draw.text(
            (x, y),
            "NIKKE UNION RAID 最適化プラン",
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

        draw.text(
            (x, y),
            current_phase_text,
            font=phase_font,
            fill=self.TEXT_ACCENT,
        )

        y += 50

        summary = (
            f"攻撃数 {plan.attack_count}件"
            f"   |   総割当Damage {plan.total_nominal_damage:,}"
            f"   |   総有効Damage {plan.total_effective_damage:,}"
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
            "※ 残HPを考慮した最適化結果です",
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
                "現在、割り当て可能な最適化候補がありません。",
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

    def _resolve_phase_text(
        self,
        plan: UnionAssignmentPlan,
    ) -> str:
        """ヘッダ表示用のPhase文字列を返す。"""

        if not plan.boss_summaries:
            return "Phase -"

        phase_nos = sorted(
            {
                boss.phase_no
                for boss in plan.boss_summaries
            }
        )

        if len(phase_nos) == 1:
            return f"Phase {phase_nos[0]}"

        joined = " / ".join(
            f"Phase {phase_no}"
            for phase_no in phase_nos
        )
        return joined

    def _calculate_card_height(
        self,
        draw: ImageDraw.ImageDraw,
        boss: BossAssignmentSummary,
        small_font: ImageFont.FreeTypeFont,
    ) -> int:
        """Bossカードに必要な高さを計算する。"""

        height = 250

        max_text_width = (
            self.WIDTH
            - self.OUTER_MARGIN * 4
        )

        for assignment in boss.assignments:
            # プレイヤー行
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
            320,
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
        """Bossカードを描画する。"""

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

        y += 82

        consumed_hp = (
            boss.max_hp - boss.remaining_hp
        )

        label_x = x
        value_x = x + 220

        # HP情報
        draw.text(
            (label_x, y),
            "最大HP",
            font=small_font,
            fill=self.TEXT_SUB,
        )
        draw.text(
            (value_x, y),
            f"{boss.max_hp:,}",
            font=small_font,
            fill=self.TEXT_ACCENT,
        )
        y += 30

        draw.text(
            (label_x, y),
            "現在残HP",
            font=small_font,
            fill=self.TEXT_SUB,
        )
        draw.text(
            (value_x, y),
            f"{boss.remaining_hp:,}",
            font=small_font,
            fill=self.TEXT_ACCENT,
        )
        y += 30

        draw.text(
            (label_x, y),
            "消化済HP",
            font=small_font,
            fill=self.TEXT_SUB,
        )
        draw.text(
            (value_x, y),
            f"{consumed_hp:,}",
            font=small_font,
            fill=self.TEXT_ACCENT,
        )
        y += 42

        # Damage情報
        draw.text(
            (label_x, y),
            "割当Damage",
            font=small_font,
            fill=self.TEXT_SUB,
        )
        draw.text(
            (value_x, y),
            f"{boss.assigned_damage:,}",
            font=small_font,
            fill=self.TEXT_ACCENT,
        )
        y += 30

        draw.text(
            (label_x, y),
            "有効Damage",
            font=small_font,
            fill=self.TEXT_SUB,
        )
        draw.text(
            (value_x, y),
            f"{boss.effective_damage:,}",
            font=small_font,
            fill=self.TEXT_ACCENT,
        )
        y += 30

        draw.text(
            (label_x, y),
            "Overkill",
            font=small_font,
            fill=self.TEXT_SUB,
        )
        draw.text(
            (value_x, y),
            f"{boss.overkill_damage:,}",
            font=small_font,
            fill=self.TEXT_ACCENT,
        )
        y += 42

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

    def build_summary_text(
        self,
        plan: UnionAssignmentPlan,
        raid_name: str,
        generated_at: datetime | None = None,
    ) -> str:
        """Discord本文用の要約テキストを生成する。"""

        if generated_at is None:
            generated_at = datetime.now()

        phase_text = self._resolve_phase_text(
            plan
        )

        boss_names = [
            boss.boss_name
            for boss in plan.boss_summaries
        ]

        lines: list[str] = []

        lines.append(
            "NIKKE UNION RAID 最適化プラン"
        )
        lines.append(
            f"Raid: {raid_name}"
        )
        lines.append(
            f"Phase: {phase_text}"
        )
        lines.append(
            f"対象Boss数: {len(plan.boss_summaries)}"
        )
        lines.append(
            f"採用攻撃数: {plan.attack_count}"
        )
        lines.append(
            f"総割当Damage: {plan.total_nominal_damage:,}"
        )
        lines.append(
            f"総有効Damage: {plan.total_effective_damage:,}"
        )
        lines.append("")

        if boss_names:
            lines.append("対象Boss:")
            for boss_name in boss_names:
                lines.append(
                    f"- {boss_name}"
                )
            lines.append("")
        else:
            lines.append(
                "対象Bossはありません。"
            )
            lines.append("")

        lines.append(
            "各Bossの詳細は添付画像を参照してください。"
        )
        lines.append(
            f"更新時刻: {generated_at:%Y-%m-%d %H:%M:%S}"
        )

        return "\n".join(lines)


    def render_boss_images(
        self,
        plan: UnionAssignmentPlan,
    ) -> list[RenderedBossImage]:
        """Bossごとの詳細画像を生成する。"""

        rendered: list[RenderedBossImage] = []

        for index, boss in enumerate(
            plan.boss_summaries,
            start=1,
        ):
            png_bytes = self._render_single_boss(
                boss
            )

            safe_name = self._sanitize_filename(
                boss.boss_name
            )

            rendered.append(
                RenderedBossImage(
                    filename=(
                        f"{index:02d}_{safe_name}.png"
                    ),
                    boss_name=boss.boss_name,
                    png_bytes=png_bytes,
                )
            )

        return rendered

    def _sanitize_filename(
        self,
        name: str,
    ) -> str:
        sanitized = re.sub(
            r'[\\/:*?"<>|]+',
            "_",
            name,
        ).strip()

        if not sanitized:
            return "boss"

        return sanitized


    def _resolve_phase_text(
        self,
        plan: UnionAssignmentPlan,
    ) -> str:
        if not plan.boss_summaries:
            return "-"

        phase_nos = sorted(
            {
                boss.phase_no
                for boss in plan.boss_summaries
            }
        )

        if len(phase_nos) == 1:
            return str(phase_nos[0])

        return " / ".join(
            str(phase_no)
            for phase_no in phase_nos
        )

    def _render_single_boss(
        self,
        boss: BossAssignmentSummary,
    ) -> bytes:
        title_font = self._load_font(
            48,
            bold=True,
        )

        header_font = self._load_font(
            28,
            bold=True,
        )

        normal_font = self._load_font(
            24,
        )

        small_font = self._load_font(
            20,
        )

        dummy = Image.new(
            "RGB",
            (1, 1),
        )

        dummy_draw = ImageDraw.Draw(
            dummy
        )

        height = self._calculate_single_boss_height(
            draw=dummy_draw,
            boss=boss,
            small_font=small_font,
        )

        image = Image.new(
            "RGB",
            (self.WIDTH, height),
            self.BACKGROUND,
        )

        draw = ImageDraw.Draw(
            image
        )

        left = self.OUTER_MARGIN
        right = self.WIDTH - self.OUTER_MARGIN

        draw.rounded_rectangle(
            (
                left,
                self.OUTER_MARGIN,
                right,
                height - self.OUTER_MARGIN,
            ),
            radius=24,
            fill=self.CARD_BACKGROUND,
            outline=self.CARD_BORDER,
            width=2,
        )

        x = left + 28
        y = self.OUTER_MARGIN + 24

        draw.text(
            (x, y),
            boss.boss_name,
            font=title_font,
            fill=self.TEXT_MAIN,
        )

        y += 58

        draw.text(
            (x, y),
            f"Phase {boss.phase_no}",
            font=header_font,
            fill=self.TEXT_ACCENT,
        )

        y += 54

        # ============================================
        # 現在HP / 最大HP
        # ============================================

        current_hp_text = (
            f"{boss.remaining_hp:,} / {boss.max_hp:,}"
        )

        self._draw_kv_line(
            draw=draw,
            x=x,
            y=y,
            label="現在HP / 最大HP",
            value=current_hp_text,
            label_font=small_font,
            value_font=small_font,
        )

        y += 34

        self._draw_hp_bar(
            draw=draw,
            x=x,
            y=y,
            width=820,
            height=22,
            total=max(1, boss.max_hp),
            remaining=max(0, boss.remaining_hp),
        )

        remaining_rate = (
            boss.remaining_hp / boss.max_hp
            if boss.max_hp > 0
            else 0.0
        )

        draw.text(
            (x + 840, y - 2),
            f"残り {remaining_rate * 100:.1f}%",
            font=small_font,
            fill=self.TEXT_SUB,
        )

        y += 54

        # ============================================
        # 割り当てダメージ
        # ============================================

        self._draw_kv_line(
            draw=draw,
            x=x,
            y=y,
            label="割り当てダメージ",
            value=f"{boss.assigned_damage:,}",
            label_font=small_font,
            value_font=small_font,
        )

        y += 34

        # ============================================
        # ダメージ効率
        # 計算式:
        # 最大HP ÷ (最大HP - 現在HP + 割り当てダメージ)
        # ============================================

        efficiency_denominator = (
            boss.max_hp
            - boss.remaining_hp
            + boss.assigned_damage
        )

        if efficiency_denominator <= 0:
            damage_efficiency_text = (
                "撃破に必要なダメージが足りません"
            )
        else:
            damage_efficiency = (
                boss.max_hp
                / efficiency_denominator
            )

            if damage_efficiency > 1.0:
                damage_efficiency_text = (
                    "撃破に必要なダメージが足りません"
                )
            else:
                damage_efficiency_text = (
                    f"{damage_efficiency * 100:.1f}%"
                )

        self._draw_kv_line(
            draw=draw,
            x=x,
            y=y,
            label="ダメージ効率",
            value=damage_efficiency_text,
            label_font=small_font,
            value_font=small_font,
        )

        y += 56

        draw.text(
            (x, y),
            "推奨凸編成",
            font=header_font,
            fill=self.TEXT_MAIN,
        )

        y += 42

        for assignment in boss.assignments:
            y = self._draw_assignment_block(
                image=image,
                draw=draw,
                assignment=assignment,
                base_max_hp=max(
                    1,
                    boss.max_hp,
                ),
                x=x,
                y=y,
                normal_font=normal_font,
                small_font=small_font,
            )

        output = BytesIO()

        image.save(
            output,
            format="PNG",
            optimize=True,
        )

        return output.getvalue()

    def _calculate_single_boss_height(
        self,
        draw: ImageDraw.ImageDraw,
        boss: BossAssignmentSummary,
        small_font: ImageFont.FreeTypeFont,
    ) -> int:
        height = 470

        max_width = (
            self.WIDTH
            - self.OUTER_MARGIN * 4
        )

        for assignment in boss.assignments:
            height += 42
            height += 30
            height += self.ICON_SIZE + 16

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
                    max_width=max_width,
                )

                height += len(wrapped) * 26

            height += 22

        return max(height, 620)


    def _draw_kv_line(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        label: str,
        value: str,
        label_font: ImageFont.FreeTypeFont,
        value_font: ImageFont.FreeTypeFont,
    ) -> None:
        draw.text(
            (x, y),
            label,
            font=label_font,
            fill=self.TEXT_SUB,
        )

        draw.text(
            (x + 180, y),
            value,
            font=value_font,
            fill=self.TEXT_ACCENT,
        )


    def _draw_bar_background(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        draw.rounded_rectangle(
            (
                x,
                y,
                x + width,
                y + height,
            ),
            radius=10,
            fill=(60, 65, 75),
        )


    def _draw_hp_bar(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        width: int,
        height: int,
        total: int,
        remaining: int,
    ) -> None:
        self._draw_bar_background(
            draw=draw,
            x=x,
            y=y,
            width=width,
            height=height,
        )

        consumed_ratio = max(
            0.0,
            min(
                1.0,
                (total - remaining) / total,
            ),
        )

        remaining_ratio = max(
            0.0,
            min(
                1.0,
                remaining / total,
            ),
        )

        consumed_width = int(
            width * consumed_ratio
        )

        remaining_width = int(
            width * remaining_ratio
        )

        if consumed_width > 0:
            draw.rounded_rectangle(
                (
                    x,
                    y,
                    x + consumed_width,
                    y + height,
                ),
                radius=10,
                fill=(110, 110, 110),
            )

        if remaining_width > 0:
            draw.rounded_rectangle(
                (
                    x + consumed_width,
                    y,
                    x + consumed_width + remaining_width,
                    y + height,
                ),
                radius=10,
                fill=(70, 160, 255),
            )


    def _draw_damage_bar(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        width: int,
        height: int,
        remaining_hp: int,
        effective_damage: int,
        overkill_damage: int,
    ) -> None:
        self._draw_bar_background(
            draw=draw,
            x=x,
            y=y,
            width=width,
            height=height,
        )

        effective_ratio = max(
            0.0,
            min(
                1.0,
                effective_damage / remaining_hp,
            ),
        )

        effective_width = int(
            width * effective_ratio
        )

        if effective_width > 0:
            draw.rounded_rectangle(
                (
                    x,
                    y,
                    x + effective_width,
                    y + height,
                ),
                radius=10,
                fill=(80, 210, 120),
            )

        if overkill_damage > 0:
            overkill_ratio = max(
                0.0,
                min(
                    1.0,
                    overkill_damage / remaining_hp,
                ),
            )

            overkill_width = max(
                10,
                int(width * overkill_ratio),
            )

            draw.rounded_rectangle(
                (
                    x + width - overkill_width,
                    y,
                    x + width,
                    y + height,
                ),
                radius=10,
                fill=(230, 90, 90),
            )

    def _draw_assignment_block(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        assignment: AttackAssignment,
        base_max_hp: int,
        x: int,
        y: int,
        normal_font: ImageFont.FreeTypeFont,
        small_font: ImageFont.FreeTypeFont,
    ) -> int:
        attack_text = (
            f"{assignment.player_name}"
            f" / Team #{assignment.team_no}"
            f" / {assignment.damage:,}"
        )

        draw.text(
            (x, y),
            attack_text,
            font=normal_font,
            fill=self.TEXT_MAIN,
        )

        y += 34

        ratio = (
            assignment.damage / base_max_hp
            if base_max_hp > 0
            else 0.0
        )

        draw.text(
            (x, y),
            f"割合: {ratio * 100:.1f}%",
            font=small_font,
            fill=self.TEXT_SUB,
        )

        y += 30

        icon_x = x
        missing_names: list[str] = []

        for character_name in assignment.character_names:
            icon = self.icon_loader.get_icon(
                character_name
            )

            if icon is not None:
                image.paste(
                    icon,
                    (icon_x, y),
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

        y += self.ICON_SIZE + 14

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
                max_width=900,
            )

            for line in wrapped:
                draw.text(
                    (x, y),
                    line,
                    font=small_font,
                    fill=self.TEXT_SUB,
                )
                y += 24

        y += 14

        return y