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
            1: 150_841_813_600,
            2: 226_262_720_400,
            3: 349_230_901_500,
        },
    ),

    BossMaster(
        key="sunbather",
        name="サンバス",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="plate",
        name="プレート",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="chatterbox",
        name="トーカティブ",
        phase_hps={
            1: 150_841_813_600,
            2: 226_262_720_400,
            3: 349_230_901_500,
        },
    ),

    BossMaster(
        key="rebuild_fingers",
        name="リビルドフィンガーズ",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="material_h",
        name="マテリアルH",
        phase_hps={
            1: 150_841_813_600,
            2: 226_262_720_400,
            3: 349_230_901_500,
        },
    ),

    BossMaster(
        key="mace",
        name="ドリアン",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="doctor",
        name="ドクター",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="alteisen",
        name="アルトアイゼン",
        phase_hps={
            1: 150_841_813_600,
            2: 226_262_720_400,
            3: 349_230_901_500,
        },
    ),

    BossMaster(
        key="rebuild_obelisk",
        name="リビルドオベリスク",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="kraken",
        name="クラーケン",
        phase_hps={
            1: 150_841_813_600,
            2: 226_262_720_400,
            3: 349_230_901_500,
        },
    ),

    BossMaster(
        key="sinister",
        name="シニスター",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="replica_red_shoes",
        name="レッドシューズ",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="nihilister",
        name="ニヒリスター",
        phase_hps={
            1: 150_841_813_600,
            2: 226_262_720_400,
            3: 349_230_901_500,
        },
    ),

    BossMaster(
        key="rebuild_stout",
        name="リビルドビッグトルソー",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="ultra",
        name="ウルトラ",
        phase_hps={
            1: 150_841_813_600,
            2: 226_262_720_400,
            3: 349_230_901_500,
        },
    ),

    BossMaster(
        key="heavy_metal",
        name="ヘビーメタル",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="modernia",
        name="モダニア",
        phase_hps={
            1: 150_841_813_600,
            2: 226_262_720_400,
            3: 349_230_901_500,
        },
    ),

    BossMaster(
        key="rebuild_vulcan_r",
        name="リビルドバルカン",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="spread",
        name="スプレッド",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="crystal_armor",
        name="クリスタルアーマー",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="rebuild_cucumber",
        name="リビルドキューカンバー",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="storm_bringer",
        name="ストームブリンガー",
        phase_hps={
            1: 150_841_813_600,
            2: 226_262_720_400,
            3: 349_230_901_500,
        },
    ),

    BossMaster(
        key="porter",
        name="ポーター",
        phase_hps={
            1: 99_856_279_200,
            2: 149_784_418_800,
            3: 292_445_295_750,
        },
    ),

    BossMaster(
        key="plate",
        name="プレート",
        phase_hps={
            1: 150_841_813_600,
            2: 226_262_720_400,
            3: 349_230_901_500,
        },
    ),

    # 今後ここへBossを追加する。
    #
    #BossMaster(
    #    key="",
    #    name="",
    #    phase_hps={
    #        1: ___,
    #        2: ___,
    #        3: ___,
    #    },
    #),
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