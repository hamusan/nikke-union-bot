from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot.models import Base


DATABASE_DIR = Path("database")
DATABASE_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "nikke.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"


engine = create_engine(
    DATABASE_URL,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def initialize_database() -> None:
    """データベースとテーブルを初期化する。"""

    Base.metadata.create_all(bind=engine)