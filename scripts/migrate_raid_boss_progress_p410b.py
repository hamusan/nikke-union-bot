from __future__ import annotations

import sqlite3
from pathlib import Path


DATABASE_PATH = Path(
    "database/nikke.db"
)


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            (
                "Database not found: "
                f"{DATABASE_PATH}"
            )
        )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS
            raid_boss_progress (
                id INTEGER
                    PRIMARY KEY AUTOINCREMENT,

                boss_phase_id INTEGER
                    NOT NULL UNIQUE,

                remaining_hp INTEGER
                    NOT NULL
                    CHECK (remaining_hp >= 0),

                updated_at DATETIME
                    NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (boss_phase_id)
                    REFERENCES boss_phases(id)
                    ON DELETE CASCADE
            )
            """
        )

        # ------------------------------------
        # 既存BossPhaseを初期化
        # ------------------------------------
        #
        # まだProgressが存在しないBossPhaseだけ
        # remaining_hp = max_hp
        # として登録する。
        #
        # 既存Progressは絶対に上書きしない。
        # ------------------------------------

        connection.execute(
            """
            INSERT INTO raid_boss_progress (
                boss_phase_id,
                remaining_hp
            )
            SELECT
                bp.id,
                bp.max_hp
            FROM boss_phases AS bp
            WHERE
                bp.max_hp > 0
                AND NOT EXISTS (
                    SELECT 1
                    FROM raid_boss_progress AS rp
                    WHERE
                        rp.boss_phase_id
                        = bp.id
                )
            """
        )

        connection.commit()

        print(
            "raid_boss_progress migration OK"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()