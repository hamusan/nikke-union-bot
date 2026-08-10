from sqlalchemy import inspect

from bot.core.database import engine
from bot.models.raid_attack_cancellation import (
    RaidAttackCancellation,
)


TABLE_NAME = "raid_attack_cancellations"


def main() -> None:
    inspector = inspect(engine)

    existing_tables = set(
        inspector.get_table_names()
    )

    if TABLE_NAME in existing_tables:
        print(
            "[SKIP] "
            f"{TABLE_NAME} already exists"
        )
        return

    RaidAttackCancellation.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    print(
        "[OK] "
        f"{TABLE_NAME} created"
    )


if __name__ == "__main__":
    main()