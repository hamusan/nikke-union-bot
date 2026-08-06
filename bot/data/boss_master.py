from dataclasses import dataclass


@dataclass(frozen=True)
class BossMaster:
    """
    ゲーム内に実装されている固定Boss情報。

    key:
        Bot内部で使用する固定ID。

    name:
        ゲーム画面に表示されるBoss名。

    phase_hps:
        phase_no -> max_hp
    """

    key: str
    name: str
    phase_hps: dict[int, int]


# ============================================================
# Boss Master
#
# Boss名・Phase・最大HPの正式な定義は
# このファイルだけで管理する。
# ============================================================

BOSS_MASTERS: tuple[
    BossMaster,
    ...
] = (
    BossMaster(
        key="grave_digger",
        name="グレイブディガー",
        phase_hps={
            3: 150_841_811_600,
        },
    ),

    # 今後ここへBossを追加する。
    #
    # BossMaster(
    #     key="example_boss",
    #     name="ボス名",
    #     phase_hps={
    #         1: 100_000_000_000,
    #         2: 200_000_000_000,
    #         3: 300_000_000_000,
    #     },
    # ),
)


BOSS_BY_KEY: dict[
    str,
    BossMaster,
] = {
    boss.key: boss
    for boss in BOSS_MASTERS
}


BOSS_BY_NAME: dict[
    str,
    BossMaster,
] = {
    boss.name: boss
    for boss in BOSS_MASTERS
}


def get_boss_by_key(
    boss_key: str,
) -> BossMaster | None:
    """内部keyからBossを取得する。"""

    return BOSS_BY_KEY.get(
        boss_key
    )


def get_boss_by_name(
    boss_name: str,
) -> BossMaster | None:
    """表示名からBossを取得する。"""

    return BOSS_BY_NAME.get(
        boss_name
    )


def get_all_bosses() -> tuple[
    BossMaster,
    ...
]:
    """全Boss Masterを取得する。"""

    return BOSS_MASTERS


def get_all_boss_names() -> tuple[
    str,
    ...
]:
    """全Boss名を取得する。"""

    return tuple(
        boss.name
        for boss in BOSS_MASTERS
    )


def get_boss_phase_hp(
    boss_key: str,
    phase_no: int,
) -> int | None:
    """
    Boss key + Phaseから最大HPを取得する。
    """

    boss = get_boss_by_key(
        boss_key
    )

    if boss is None:
        return None

    return boss.phase_hps.get(
        phase_no
    )


def resolve_phase_no(
    boss_key: str,
    max_hp: int,
) -> int | None:
    """
    Boss key + 最大HPからPhaseを特定する。

    内部処理用。
    """

    boss = get_boss_by_key(
        boss_key
    )

    if boss is None:
        return None

    for (
        phase_no,
        phase_hp,
    ) in boss.phase_hps.items():
        if phase_hp == max_hp:
            return phase_no

    return None


def resolve_phase_no_by_name(
    boss_name: str,
    max_hp: int,
) -> int | None:
    """
    Boss表示名 + 最大HPからPhaseを特定する。

    OCR結果からPhaseを特定するときに使用する。
    """

    boss = get_boss_by_name(
        boss_name
    )

    if boss is None:
        return None

    for (
        phase_no,
        phase_hp,
    ) in boss.phase_hps.items():
        if phase_hp == max_hp:
            return phase_no

    return None


def validate_boss_master() -> None:
    """Boss Masterの設定ミスを検出する。"""

    keys: set[str] = set()
    names: set[str] = set()

    for boss in BOSS_MASTERS:
        if not boss.key:
            raise ValueError(
                "Boss keyが空です。"
            )

        if not boss.name:
            raise ValueError(
                (
                    "Boss nameが空です: "
                    f"{boss.key}"
                )
            )

        if boss.key in keys:
            raise ValueError(
                (
                    "Boss keyが重複しています: "
                    f"{boss.key}"
                )
            )

        if boss.name in names:
            raise ValueError(
                (
                    "Boss nameが重複しています: "
                    f"{boss.name}"
                )
            )

        if not boss.phase_hps:
            raise ValueError(
                (
                    "Phase HPがありません: "
                    f"{boss.key}"
                )
            )

        phase_hps_seen: set[int] = set()

        for (
            phase_no,
            max_hp,
        ) in boss.phase_hps.items():
            if phase_no <= 0:
                raise ValueError(
                    (
                        "Phase番号が不正です: "
                        f"{boss.key}, "
                        f"phase={phase_no}"
                    )
                )

            if max_hp <= 0:
                raise ValueError(
                    (
                        "最大HPが不正です: "
                        f"{boss.key}, "
                        f"phase={phase_no}"
                    )
                )

            # 同じBoss内でHPが同じPhaseが複数あると、
            # OCRのHPからPhaseを一意に判定できない。
            if max_hp in phase_hps_seen:
                raise ValueError(
                    (
                        "同じBoss内で最大HPが"
                        "重複しています: "
                        f"{boss.key}, "
                        f"max_hp={max_hp}"
                    )
                )

            phase_hps_seen.add(
                max_hp
            )

        keys.add(
            boss.key
        )

        names.add(
            boss.name
        )