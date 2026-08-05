from bot.core.bot import create_bot
from bot.core.database import initialize_database
from bot.core.logger import get_logger


logger = get_logger()


def main() -> None:
    bot, config = create_bot()

    logger.info("Logger initialized")

    initialize_database()
    logger.info("Database initialized")

    bot.run(config.discord_token)


if __name__ == "__main__":
    main()