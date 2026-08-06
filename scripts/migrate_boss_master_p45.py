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
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(bosses)"
            )
        }

        if "boss_key" not in columns:
            print(
                "boss_key を追加します..."
            )

            connection.execute(
                """
                ALTER TABLE bosses
                ADD COLUMN boss_key VARCHAR(100)
                """
            )

        else:
            print(
                "boss_key は既に存在します。"
            )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            ix_bosses_boss_key
            ON bosses (boss_key)
            """
        )

        # 同じRaidに同じBoss Masterを
        # 2体配置できないようにする。
        #
        # 既存行のboss_key=NULLには影響しない。
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            uq_bosses_raid_boss_key
            ON bosses (raid_id, boss_key)
            WHERE boss_key IS NOT NULL
            """
        )

        connection.commit()

        print()
        print("Migration完了")
        print("------------------------------")

        new_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(bosses)"
            )
        }

        print(
            "boss_key:",
            "boss_key" in new_columns,
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()