from pathlib import Path
import sqlite3

from bot.data import BOSS_MASTERS


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

        active_raid = connection.execute(
            """
            SELECT id, name
            FROM raids
            WHERE active = 1
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        if active_raid is None:
            raise RuntimeError(
                "Active Raidがありません。"
            )

        raid_id = int(
            active_raid[0]
        )

        print(
            f"Active Raid ID: {raid_id}"
        )

        print()

        for master in BOSS_MASTERS:
            boss_row = connection.execute(
                """
                SELECT id, boss_no, name, boss_key
                FROM bosses
                WHERE raid_id = ?
                  AND name = ?
                LIMIT 1
                """,
                (
                    raid_id,
                    master.name,
                ),
            ).fetchone()

            # このRaidで採用されていないBoss Masterは
            # 何もしない。
            if boss_row is None:
                print(
                    f"SKIP: {master.name} "
                    "(Active Raidに存在しません)"
                )
                continue

            boss_id = int(
                boss_row[0]
            )

            boss_no = int(
                boss_row[1]
            )

            current_key = boss_row[3]

            print(
                f"Boss #{boss_no}: "
                f"{master.name}"
            )

            # --------------------------------
            # boss_keyを既存Bossへ紐付け
            # --------------------------------

            if (
                current_key is not None
                and current_key != master.key
            ):
                raise RuntimeError(
                    (
                        "既存Bossに別のboss_keyが"
                        "設定されています: "
                        f"boss_id={boss_id}, "
                        f"current={current_key}, "
                        f"master={master.key}"
                    )
                )

            connection.execute(
                """
                UPDATE bosses
                SET boss_key = ?
                WHERE id = ?
                """,
                (
                    master.key,
                    boss_id,
                ),
            )

            print(
                f"  boss_key = {master.key}"
            )

            # --------------------------------
            # BossPhaseをMasterから同期
            # --------------------------------

            for (
                phase_no,
                max_hp,
            ) in sorted(
                master.phase_hps.items()
            ):
                existing_phase = (
                    connection.execute(
                        """
                        SELECT id, max_hp
                        FROM boss_phases
                        WHERE boss_id = ?
                          AND phase_no = ?
                        LIMIT 1
                        """,
                        (
                            boss_id,
                            phase_no,
                        ),
                    ).fetchone()
                )

                if existing_phase is None:
                    connection.execute(
                        """
                        INSERT INTO boss_phases (
                            boss_id,
                            phase_no,
                            max_hp
                        )
                        VALUES (?, ?, ?)
                        """,
                        (
                            boss_id,
                            phase_no,
                            max_hp,
                        ),
                    )

                    print(
                        f"  Phase {phase_no}: "
                        f"CREATE {max_hp:,}"
                    )

                else:
                    phase_id = int(
                        existing_phase[0]
                    )

                    old_hp = int(
                        existing_phase[1]
                    )

                    if old_hp != max_hp:
                        connection.execute(
                            """
                            UPDATE boss_phases
                            SET max_hp = ?
                            WHERE id = ?
                            """,
                            (
                                max_hp,
                                phase_id,
                            ),
                        )

                        print(
                            f"  Phase {phase_no}: "
                            f"UPDATE "
                            f"{old_hp:,} -> {max_hp:,}"
                        )

                    else:
                        print(
                            f"  Phase {phase_no}: "
                            "OK"
                        )

        connection.commit()

        print()
        print(
            "Boss Master backfill完了"
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()