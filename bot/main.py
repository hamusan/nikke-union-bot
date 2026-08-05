from bot.core.bot import create_bot
from bot.core.logger import get_logger


logger = get_logger()


def main():

    bot, config = create_bot()

    logger.info("Logger initialized")

    bot.run(config.discord_token)


if __name__ == "__main__":
    main()