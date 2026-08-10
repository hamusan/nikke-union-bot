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
            raid_attacks (
                id INTEGER
                    PRIMARY KEY AUTOINCREMENT,

                raid_id INTEGER
                    NOT NULL,

                phase_no INTEGER
                    NOT NULL
                    CHECK (
                        phase_no >= 1
                        AND phase_no <= 3
                    ),

                boss_id INTEGER
                    NOT NULL,

                player_id INTEGER
                    NOT NULL,

                team_id INTEGER
                    NOT NULL,

                damage INTEGER
                    NOT NULL
                    CHECK (damage >= 0),

                source_message_id INTEGER
                    UNIQUE,

                image_sha256 VARCHAR(64)
                    UNIQUE,

                created_at DATETIME
                    NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (raid_id)
                    REFERENCES raids(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (boss_id)
                    REFERENCES bosses(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (player_id)
                    REFERENCES players(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (team_id)
                    REFERENCES teams(id)
                    ON DELETE CASCADE
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            ix_raid_attacks_raid_id
            ON raid_attacks (raid_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            ix_raid_attacks_phase_no
            ON raid_attacks (phase_no)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            ix_raid_attacks_boss_id
            ON raid_attacks (boss_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            ix_raid_attacks_player_id
            ON raid_attacks (player_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            ix_raid_attacks_team_id
            ON raid_attacks (team_id)
            """
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            ix_raid_attacks_source_message_id
            ON raid_attacks (source_message_id)
            WHERE source_message_id IS NOT NULL
            """
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            ix_raid_attacks_image_sha256
            ON raid_attacks (image_sha256)
            WHERE image_sha256 IS NOT NULL
            """
        )

        connection.commit()

        print(
            "raid_attacks migration OK"
        )

    finally:
        connection.close()


if __name__ == "__main__":
    main()