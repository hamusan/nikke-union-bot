import discord
from discord.ext import commands

from bot.core.config import Config, load_config
from bot.core.logger import get_logger


logger = get_logger()


EXTENSIONS = (
    "bot.cogs.ping",
    "bot.cogs.player",
    "bot.cogs.team",
    "bot.cogs.raid",
)


class NikkeBot(commands.Bot):
    """NIKKE Union Raid Bot本体。"""

    def __init__(self, config: Config) -> None:
        intents = discord.Intents.default()

        super().__init__(
            command_prefix="!",
            intents=intents,
        )

        self.config = config

    async def setup_hook(self) -> None:
        """Discord接続前の初期化処理。"""

        for extension in EXTENSIONS:
            await self.load_extension(extension)

            logger.info(
                "Extension loaded: {}",
                extension,
            )

        guild = discord.Object(
            id=self.config.guild_id
        )

        # 開発中はGuild単位で同期することで、
        # スラッシュコマンドをすぐ反映させる。
        self.tree.copy_global_to(guild=guild)

        synced_commands = await self.tree.sync(
            guild=guild
        )

        logger.info(
            "Synced {} application command(s) to guild {}",
            len(synced_commands),
            self.config.guild_id,
        )

    async def on_ready(self) -> None:
        logger.info(
            "Logged in as {}",
            self.user,
        )


def create_bot() -> tuple[NikkeBot, Config]:
    """Botインスタンスを生成する。"""

    config = load_config()

    bot = NikkeBot(config)

    return bot, config