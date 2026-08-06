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

        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(damage_records)"
            )
        }

        print(
            "現在のcolumns:",
            sorted(columns),
        )

        if "boss_phase_id" not in columns:
            print(
                "boss_phase_id を追加します..."
            )

            connection.execute(
                """
                ALTER TABLE damage_records
                ADD COLUMN boss_phase_id INTEGER
                REFERENCES boss_phases(id)
                """
            )
        else:
            print(
                "boss_phase_id は既に存在します。"
            )

        if "image_sha256" not in columns:
            print(
                "image_sha256 を追加します..."
            )

            connection.execute(
                """
                ALTER TABLE damage_records
                ADD COLUMN image_sha256 VARCHAR(64)
                """
            )
        else:
            print(
                "image_sha256 は既に存在します。"
            )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            ix_damage_records_boss_phase_id
            ON damage_records (boss_phase_id)
            """
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            ix_damage_records_image_sha256
            ON damage_records (image_sha256)
            WHERE image_sha256 IS NOT NULL
            """
        )

        connection.commit()

        new_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(damage_records)"
            )
        }

        print()
        print("Migration完了")
        print("------------------------------")
        print(
            "boss_phase_id:",
            "boss_phase_id" in new_columns,
        )
        print(
            "image_sha256:",
            "image_sha256" in new_columns,
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()