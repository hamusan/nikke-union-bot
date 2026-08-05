from bot.core.database import session_scope
from bot.repositories import (
    CharacterRepository,
    PlayerRepository,
    TeamRepository,
)


DISCORD_ID = "507895244340068364"


CHARACTER_NAMES = [
    "クラウン",
    "リター",
    "レッドフード",
    "ナガ",
    "モダニア",
]


def main() -> None:
    with session_scope() as session:
        player_repository = PlayerRepository(session)
        character_repository = CharacterRepository(session)
        team_repository = TeamRepository(session)

        player = player_repository.get_by_discord_id(
            DISCORD_ID
        )

        if player is None:
            raise RuntimeError(
                "Playerが登録されていません。"
            )

        team = team_repository.get_by_player_and_name(
            player_id=player.id,
            team_name="テスト編成",
        )

        if team is None:
            team = team_repository.create(
                player_id=player.id,
                team_name="テスト編成",
                memo="Repository動作確認用",
            )

            for position, name in enumerate(
                CHARACTER_NAMES,
                start=1,
            ):
                character = character_repository.get_by_name(
                    name
                )

                if character is None:
                    character = character_repository.create(
                        name=name
                    )

                team_repository.add_member(
                    team=team,
                    character=character,
                    position=position,
                )

        team_id = team.id

    # 一度Sessionを閉じてから、
    # DBから本当に読み直せるか確認する。
    with session_scope() as session:
        team_repository = TeamRepository(session)

        team = team_repository.get_by_id(
            team_id
        )

        if team is None:
            raise RuntimeError(
                "Teamを取得できませんでした。"
            )

        print()
        print(f"Team ID   : {team.id}")
        print(f"Team Name : {team.team_name}")
        print()

        for member in team.members:
            print(
                f"{member.position}: "
                f"{member.character.name}"
            )


if __name__ == "__main__":
    main()