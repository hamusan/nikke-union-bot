from __future__ import annotations

import sqlite3
from pathlib import Path


DATABASE_PATH = Path(
    "database/nikke.db"
)


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:
        columns = {
            row[1]
            for row in connection.execute(
                """
                PRAGMA table_info(raids)
                """
            ).fetchall()
        }

        if "current_phase" in columns:
            print(
                "current_phase already exists."
            )
            return

        connection.execute(
            """
            ALTER TABLE raids
            ADD COLUMN current_phase
            INTEGER NOT NULL DEFAULT 1
            """
        )

        connection.commit()

        print(
            "Added raids.current_phase."
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()