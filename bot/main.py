from bot.constants import BOT_NAME
from bot.core.bot import create_bot
from bot.core.database import initialize_database
from bot.core.logger import get_logger
from bot.version import VERSION


logger = get_logger()


def main() -> None:
    logger.info(
        "Starting {} v{}",
        BOT_NAME,
        VERSION,
    )

    bot, config = create_bot()

    initialize_database()
    logger.info("Database initialized")

    bot.run(config.discord_token)


if __name__ == "__main__":
    main()