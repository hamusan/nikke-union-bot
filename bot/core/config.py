from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """アプリケーション設定"""

    discord_token: str
    guild_id: str


def load_config() -> Config:
    """.env を読み込んで Config を生成する"""

    load_dotenv()

    return Config(
        discord_token=os.getenv("DISCORD_TOKEN", ""),
        guild_id=os.getenv("GUILD_ID", ""),
    )