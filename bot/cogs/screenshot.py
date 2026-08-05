from pathlib import Path

import discord
from discord.ext import commands

from bot.core.logger import get_logger


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

        SCREENSHOT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message,
    ) -> None:
        """指定チャンネルへ投稿された画像を保存する。"""

        if message.author.bot:
            return

        if (
            message.channel.id
            != self.screenshot_channel_id
        ):
            return

        if not message.attachments:
            return

        saved_count = 0

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
                    (
                        "画像サイズが大きすぎます。"
                        "20MB以下の画像を投稿してください。"
                    )
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
                continue

            saved_count += 1

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

        if saved_count > 0:
            await message.reply(
                (
                    f"画像を **{saved_count}枚** "
                    "受け取りました。\n"
                    "現在は保存まで確認しています。"
                )
            )


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        ScreenshotCog(bot)
    )