from pathlib import Path


CHARACTER_ICON_DIR = Path(
    "assets/character_icons"
)

CHARACTER_ICON_MAP: dict[str, str] = {
    "シンデレラ": "cinderella.png",
    "レッドフード": "red_hood.png",
    "ヘルム": "helm.png",
    "ベスティー": "vesti.png",
    "ベスティー：タクティカル・アップ": "vesti_tactical_up.png",
}


def resolve_character_icon_path(
    character_name: str,
) -> Path | None:
    """
    キャラ名から表示用アイコンのPathを返す。
    登録が無い場合はNone。
    """

    filename = CHARACTER_ICON_MAP.get(
        character_name
    )

    if filename is None:
        return None

    return CHARACTER_ICON_DIR / filename