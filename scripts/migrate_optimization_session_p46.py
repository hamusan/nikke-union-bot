from pathlib import Path
import sqlite3


DATABASE_PATH = Path(
    "database/nikke.db"
)


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"DBが存在しません: {DATABASE_PATH}"
        )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS
            optimization_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                channel_id BIGINT NOT NULL UNIQUE,
                message_id BIGINT,

                raid_id INTEGER NOT NULL,

                interval_minutes INTEGER
                    NOT NULL
                    DEFAULT 5,

                started_by_discord_id BIGINT
                    NOT NULL,

                active BOOLEAN
                    NOT NULL
                    DEFAULT 1,

                created_at DATETIME
                    NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at DATETIME
                    NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (raid_id)
                    REFERENCES raids(id)
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            ix_optimization_sessions_raid_id
            ON optimization_sessions (raid_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            ix_optimization_sessions_active
            ON optimization_sessions (active)
            """
        )

        connection.commit()

        print(
            "optimization_sessions migration OK"
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()