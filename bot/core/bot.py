import discord

from bot.core.config import load_config
from bot.core.logger import get_logger


logger = get_logger()


class NikkeBot(discord.Client):

    async def on_ready(self):
        logger.info(f"Logged in as {self.user}")


def create_bot():

    config = load_config()

    intents = discord.Intents.default()

    bot = NikkeBot(intents=intents)

    return bot, config