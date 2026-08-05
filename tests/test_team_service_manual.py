from bot.exceptions import (
    DuplicateCharacterError,
    InvalidTeamMemberCountError,
    TeamAlreadyExistsError,
)
from bot.services import TeamService


DISCORD_ID = "507895244340068364"


def print_team(team) -> None:
    print()
    print(f"Team ID   : {team.id}")
    print(f"Team Name : {team.team_name}")
    print()

    for member in team.members:
        print(
            f"{member.position}: "
            f"{member.character.name}"
        )


def main() -> None:
    service = TeamService()

    characters = [
        "クラウン",
        "リター",
        "レッドフード",
        "ナガ",
        "モダニア",
    ]

    try:
        team = service.create_team(
            discord_id=DISCORD_ID,
            team_name="Serviceテスト編成",
            character_names=characters,
            memo="TeamService動作確認",
        )

        print("編成を作成しました。")
        print_team(team)

    except TeamAlreadyExistsError:
        print(
            "Serviceテスト編成は"
            "既に登録されています。"
        )

    print()
    print("現在の編成一覧")
    print("--------------------")

    teams = service.list_active_teams(
        DISCORD_ID
    )

    for team in teams:
        print_team(team)

    print()
    print("不正データのチェック")

    try:
        service.create_team(
            discord_id=DISCORD_ID,
            team_name="人数不足テスト",
            character_names=[
                "クラウン",
                "リター",
            ],
        )

    except InvalidTeamMemberCountError:
        print("OK: 5人未満の編成を拒否しました。")

    try:
        service.create_team(
            discord_id=DISCORD_ID,
            team_name="重複テスト",
            character_names=[
                "クラウン",
                "クラウン",
                "レッドフード",
                "ナガ",
                "モダニア",
            ],
        )

    except DuplicateCharacterError:
        print("OK: Character重複を拒否しました。")


if __name__ == "__main__":
    main()