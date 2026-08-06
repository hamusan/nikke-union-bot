import asyncio
from pathlib import Path

import discord
from discord.ext import commands

from bot.core.logger import get_logger
from bot.exceptions import (
    ActiveRaidNotFoundError,
    BossNotFoundError,
    BossPhaseNotFoundError,
)
from bot.services import (
    RaidService,
    TeamService,
)
from bot.services.ocr import (
    BattleOcrResult,
    BattleOcrService,
)
from bot.services.team_image import (
    CharacterRecognizer,
    TeamPortraitCropper,
)


logger = get_logger()


SCREENSHOT_DIR = Path(
    "uploads/screenshots"
)

CHARACTER_TEMPLATE_DIR = Path(
    "uploads/character_templates"
)

MAX_IMAGE_SIZE = (
    20 * 1024 * 1024
)


CONTENT_TYPE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


class ScreenshotCog(commands.Cog):
    """ユニオンレイドのスクリーンショット受付。"""

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:
        self.bot = bot

        config = getattr(
            bot,
            "config",
        )

        self.screenshot_channel_id = (
            config.screenshot_channel_id
        )

        self.ocr_service = BattleOcrService()
        self.raid_service = RaidService()
        self.team_service = TeamService()

        self.team_cropper = TeamPortraitCropper()

        self.character_recognizer = (
            CharacterRecognizer(
                template_dir=CHARACTER_TEMPLATE_DIR
            )
        )

        # PaddleOCRを同時実行しない。
        self.ocr_lock = asyncio.Lock()

        SCREENSHOT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message,
    ) -> None:
        """指定チャンネルへの2枚投稿を処理する。"""

        if message.author.bot:
            return

        if (
            message.channel.id
            != self.screenshot_channel_id
        ):
            return

        image_attachments = [
            attachment
            for attachment in message.attachments
            if self._get_extension(
                attachment
            ) is not None
        ]

        if not image_attachments:
            return

        if len(image_attachments) != 2:
            await message.reply(
                (
                    "ダメージ登録には画像を"
                    "**2枚同時に投稿**してください。\n\n"
                    "・ダメージ結果スクショ\n"
                    "・戦闘履歴（5キャラ）スクショ"
                )
            )
            return

        saved_paths: list[Path] = []

        for attachment in image_attachments:
            if attachment.size > MAX_IMAGE_SIZE:
                await message.reply(
                    "画像サイズは20MB以下にしてください。"
                )
                return

            extension = self._get_extension(
                attachment
            )

            if extension is None:
                continue

            filename = (
                f"{message.id}_"
                f"{attachment.id}"
                f"{extension}"
            )

            save_path = (
                SCREENSHOT_DIR
                / filename
            )

            try:
                await attachment.save(
                    save_path
                )

            except Exception:
                logger.exception(
                    (
                        "Failed to save screenshot: "
                        "message_id={}, "
                        "attachment_id={}"
                    ),
                    message.id,
                    attachment.id,
                )

                await message.reply(
                    "画像の保存に失敗しました。"
                )
                return

            saved_paths.append(
                save_path
            )

            logger.info(
                (
                    "Screenshot saved: "
                    "user_id={}, "
                    "message_id={}, "
                    "path={}"
                ),
                message.author.id,
                message.id,
                save_path,
            )

        if len(saved_paths) != 2:
            await message.reply(
                "2枚の画像を保存できませんでした。"
            )
            return

        await message.reply(
            "画像を解析しています..."
        )

        await self._process_submission(
            message=message,
            image_paths=saved_paths,
        )

    def _get_extension(
        self,
        attachment: discord.Attachment,
    ) -> str | None:
        content_type = (
            attachment.content_type
            or ""
        ).lower()

        return CONTENT_TYPE_EXTENSIONS.get(
            content_type
        )

    async def _process_submission(
        self,
        message: discord.Message,
        image_paths: list[Path],
    ) -> None:
        """2枚から結果画面と編成画面を自動判定する。"""

        try:
            bosses = (
                self.raid_service.list_bosses()
            )

        except ActiveRaidNotFoundError:
            await message.reply(
                "現在開催中のRaidがありません。"
            )
            return

        if not bosses:
            await message.reply(
                "現在のRaidにBossが登録されていません。"
            )
            return

        known_boss_names = [
            boss.name
            for boss in bosses
        ]

        result_image_path: Path | None = None
        battle_result: BattleOcrResult | None = None

        team_image_path: Path | None = None
        character_names: list[str] | None = None
        character_confidences: list[float] | None = None

        # 2枚とも調べて、
        # どちらが何の画像か自動判定する。
        for image_path in image_paths:
            if battle_result is None:
                parsed = await self._try_battle_result(
                    image_path=image_path,
                    known_boss_names=known_boss_names,
                )

                if parsed is not None:
                    result_image_path = (
                        image_path
                    )
                    battle_result = parsed

            if character_names is None:
                team_result = await self._try_team_image(
                    image_path
                )

                if team_result is not None:
                    (
                        character_names,
                        character_confidences,
                    ) = team_result

                    team_image_path = (
                        image_path
                    )

        # 同じ画像が両方として認識された場合は
        # 誤判定の可能性があるため登録しない。
        if (
            result_image_path is not None
            and team_image_path is not None
            and result_image_path == team_image_path
        ):
            await message.reply(
                (
                    "画像の種類を正しく判別できませんでした。\n"
                    "結果画面と戦闘履歴画面の"
                    "2種類を投稿してください。"
                )
            )
            return

        if battle_result is None:
            await message.reply(
                (
                    "ダメージ結果画面を"
                    "判定できませんでした。\n"
                    "Boss名・最大HP・TOTAL DAMAGEが"
                    "表示されている画像を確認してください。"
                )
            )
            return

        if character_names is None:
            await message.reply(
                (
                    "戦闘履歴画面から5キャラを"
                    "判定できませんでした。"
                )
            )
            return

        if (
            battle_result.boss_name is None
            or battle_result.boss_max_hp is None
            or battle_result.total_damage is None
        ):
            await message.reply(
                "ダメージ結果のOCR情報が不足しています。"
            )
            return

        try:
            phase = (
                self.raid_service.resolve_boss_phase(
                    boss_name=battle_result.boss_name,
                    max_hp=battle_result.boss_max_hp,
                )
            )

        except BossNotFoundError:
            await message.reply(
                (
                    f"Boss **{battle_result.boss_name}** が"
                    "DBに登録されていません。"
                )
            )
            return

        except BossPhaseNotFoundError:
            await message.reply(
                (
                    "この最大HPに対応するPhaseが"
                    "登録されていません。\n\n"
                    f"Boss: {battle_result.boss_name}\n"
                    f"最大HP: "
                    f"{battle_result.boss_max_hp:,}"
                )
            )
            return

        discord_id = str(
            message.author.id
        )

        discord_name = (
            message.author.display_name
        )

        try:
            team, team_created = (
                self.team_service
                .find_or_create_team_from_characters(
                    discord_id=discord_id,
                    discord_name=discord_name,
                    character_names=character_names,
                )
            )

        except Exception:
            logger.exception(
                (
                    "Automatic team resolution failed: "
                    "discord_id={}, characters={}"
                ),
                discord_id,
                character_names,
            )

            await message.reply(
                "編成の自動判定中にエラーが発生しました。"
            )
            return

        team_status = (
            "新規自動登録"
            if team_created
            else "既存編成と一致"
        )

        character_lines = []

        for index, name in enumerate(
            character_names,
            start=1,
        ):
            confidence = (
                character_confidences[
                    index - 1
                ]
                if character_confidences
                else 0.0
            )

            character_lines.append(
                (
                    f"{index}. {name} "
                    f"`{confidence:.3f}`"
                )
            )

        reply_text = (
            "## 自動解析結果\n\n"
            f"Player: **{discord_name}**\n"
            f"編成: **#{team.team_no}** "
            f"({team_status})\n\n"
            "**使用キャラ**\n"
            + "\n".join(
                character_lines
            )
            + "\n\n"
            f"Boss: **{battle_result.boss_name}**\n"
            f"Phase: **{phase.phase_no}**\n"
            f"最大HP: "
            f"**{battle_result.boss_max_hp:,}**\n"
            f"Damage: "
            f"**{battle_result.total_damage:,}**\n\n"
            "※ 現在は確認段階のため、"
            "DamageRecordにはまだ保存していません。"
        )

        await message.reply(
            reply_text
        )

    async def _try_battle_result(
        self,
        image_path: Path,
        known_boss_names: list[str],
        known_boss_max_hps: dict[str, list[int]],
    ) -> BattleOcrResult | None:
        """結果画面かどうかOCRで判定する。"""

        try:
            async with self.ocr_lock:
                parsed = await asyncio.to_thread(
                    self.ocr_service.analyze_image,
                    image_path,
                    known_boss_names,
                    known_boss_max_hps,
                )

        except Exception:
            logger.exception(
                "OCR failed: path={}",
                image_path,
            )
            return None

        # この3つが揃った場合のみ
        # ダメージ結果画面と判断する。
        if (
            parsed.boss_name is None
            or parsed.boss_max_hp is None
            or parsed.total_damage is None
        ):
            return None

        return parsed

    async def _try_team_image(
        self,
        image_path: Path,
    ) -> tuple[
        list[str],
        list[float],
    ] | None:
        """戦闘履歴画像かどうか判定する。"""

        try:
            crop_result = await asyncio.to_thread(
                self.team_cropper.crop,
                image_path,
            )

        except Exception:
            # 白い戦闘履歴パネルが無ければ、
            # 編成画像ではないと判断。
            return None

        character_names: list[str] = []
        confidences: list[float] = []

        for portrait in crop_result.portraits:
            result = await asyncio.to_thread(
                self.character_recognizer.recognize,
                portrait,
            )

            if result.character_name is None:
                return None

            character_names.append(
                result.character_name
            )

            confidences.append(
                result.confidence
            )

        if len(character_names) != 5:
            return None

        # 同一キャラを2人認識した場合も
        # 誤認識とみなす。
        normalized = {
            name.strip().casefold()
            for name in character_names
        }

        if len(normalized) != 5:
            return None

        return (
            character_names,
            confidences,
        )


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        ScreenshotCog(bot)
    )