from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """アプリケーション設定。"""

    discord_token: str
    guild_id: int
    screenshot_channel_id: int


def load_config() -> Config:
    """環境変数から設定を読み込む。"""

    load_dotenv()

    discord_token = os.getenv(
        "DISCORD_TOKEN",
        "",
    ).strip()

    guild_id_raw = os.getenv(
        "GUILD_ID",
        "",
    ).strip()

    screenshot_channel_id_raw = os.getenv(
        "SCREENSHOT_CHANNEL_ID",
        "",
    ).strip()

    if not discord_token:
        raise RuntimeError(
            "DISCORD_TOKEN が .env に設定されていません。"
        )

    if not guild_id_raw:
        raise RuntimeError(
            "GUILD_ID が .env に設定されていません。"
        )

    if not screenshot_channel_id_raw:
        raise RuntimeError(
            "SCREENSHOT_CHANNEL_ID が "
            ".env に設定されていません。"
        )

    try:
        guild_id = int(
            guild_id_raw
        )
    except ValueError as error:
        raise RuntimeError(
            "GUILD_ID は数字で指定してください。"
        ) from error

    try:
        screenshot_channel_id = int(
            screenshot_channel_id_raw
        )
    except ValueError as error:
        raise RuntimeError(
            "SCREENSHOT_CHANNEL_ID は"
            "数字で指定してください。"
        ) from error

    return Config(
        discord_token=discord_token,
        guild_id=guild_id,
        screenshot_channel_id=screenshot_channel_id,
    )