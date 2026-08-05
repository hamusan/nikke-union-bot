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
from bot.services import RaidService
from bot.services.ocr import (
    BattleOcrService,
)


logger = get_logger()


SCREENSHOT_DIR = Path(
    "uploads/screenshots"
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
    """ダメージスクリーンショット受付。"""

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

        # PaddleOCRを複数画像で同時実行しないためのLock。
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
        """指定チャンネルの画像を保存しOCRする。"""

        if message.author.bot:
            return

        if (
            message.channel.id
            != self.screenshot_channel_id
        ):
            return

        if not message.attachments:
            return

        for attachment in message.attachments:
            content_type = (
                attachment.content_type
                or ""
            ).lower()

            extension = (
                CONTENT_TYPE_EXTENSIONS.get(
                    content_type
                )
            )

            if extension is None:
                continue

            if attachment.size > MAX_IMAGE_SIZE:
                await message.reply(
                    "画像サイズは20MB以下にしてください。"
                )
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
                continue

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

            await self._process_image(
                message=message,
                image_path=save_path,
            )

    async def _process_image(
        self,
        message: discord.Message,
        image_path: Path,
    ) -> None:
        """保存済み画像をOCRして結果を返信する。"""

        try:
            bosses = (
                self.raid_service.list_bosses()
            )

        except ActiveRaidNotFoundError:
            await message.reply(
                (
                    "画像は保存しましたが、"
                    "現在開催中のRaidがありません。"
                )
            )
            return

        if not bosses:
            await message.reply(
                (
                    "画像は保存しましたが、"
                    "Bossが登録されていません。"
                )
            )
            return

        known_boss_names = [
            boss.name
            for boss in bosses
        ]

        try:
            # OCRはCPU負荷が高いため、
            # Discordのイベントループとは別Threadで実行する。
            async with self.ocr_lock:
                parsed = await asyncio.to_thread(
                    self.ocr_service.analyze_image,
                    image_path,
                    known_boss_names,
                )

        except Exception:
            logger.exception(
                "OCR failed: path={}",
                image_path,
            )

            await message.reply(
                "画像のOCR処理中にエラーが発生しました。"
            )
            return

        phase_no: int | None = None
        phase_error: str | None = None

        if (
            parsed.boss_name is not None
            and parsed.boss_max_hp is not None
        ):
            try:
                phase = (
                    self.raid_service.resolve_boss_phase(
                        boss_name=parsed.boss_name,
                        max_hp=parsed.boss_max_hp,
                    )
                )

                phase_no = phase.phase_no

            except BossNotFoundError:
                phase_error = (
                    "BossがDBに見つかりません。"
                )

            except BossPhaseNotFoundError:
                phase_error = (
                    "最大HPに対応するPhaseが"
                    "登録されていません。"
                )

            except Exception:
                logger.exception(
                    (
                        "Phase resolution failed: "
                        "boss={}, max_hp={}"
                    ),
                    parsed.boss_name,
                    parsed.boss_max_hp,
                )

                phase_error = (
                    "Phase判定中にエラーが発生しました。"
                )

        else:
            phase_error = (
                "Boss名または最大HPを"
                "OCRできませんでした。"
            )

        boss_text = (
            parsed.boss_name
            if parsed.boss_name is not None
            else "取得失敗"
        )

        max_hp_text = (
            f"{parsed.boss_max_hp:,}"
            if parsed.boss_max_hp is not None
            else "取得失敗"
        )

        damage_text = (
            f"{parsed.total_damage:,}"
            if parsed.total_damage is not None
            else "取得失敗"
        )

        phase_text = (
            f"Phase {phase_no}"
            if phase_no is not None
            else "判定失敗"
        )

        message_text = (
            "**OCR結果**\n\n"
            f"Boss: **{boss_text}**\n"
            f"Phase: **{phase_text}**\n"
            f"最大HP: **{max_hp_text}**\n"
            f"Damage: **{damage_text}**"
        )

        if phase_error is not None:
            message_text += (
                f"\n\nPhase判定: {phase_error}"
            )

        message_text += (
            "\n\n"
            "※ 現在は確認段階のため、"
            "DamageRecordへの自動保存はしていません。"
        )

        await message.reply(
            message_text
        )

async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        ScreenshotCog(bot)
    )