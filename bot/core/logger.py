from pathlib import Path

from loguru import logger


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


logger.remove()

logger.add(
    sink=lambda msg: print(msg, end=""),
    level="INFO",
)

logger.add(
    LOG_DIR / "bot.log",
    rotation="10 MB",
    encoding="utf-8",
    level="INFO",
)


def get_logger():
    return logger