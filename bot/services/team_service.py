from bot.core.database import session_scope
from bot.exceptions import (
    DuplicateCharacterError,
    InvalidCharacterNameError,
    InvalidTeamMemberCountError,
    InvalidTeamNameError,
    PlayerInactiveError,
    PlayerNotFoundError,
    TeamAlreadyExistsError,
    TeamAlreadyInactiveError,
    TeamNotFoundError,
)
from bot.models.team import Team
from bot.repositories import (
    CharacterRepository,
    PlayerRepository,
    TeamRepository,
)


class TeamService:
    """編成に関するアプリケーション処理を担当する。"""

    TEAM_MEMBER_COUNT = 5

    def create_team(
        self,
        discord_id: str,
        team_name: str,
        character_names: list[str],
        memo: str | None = None,
    ) -> Team:
        """5人編成を新規作成する。"""

        normalized_team_name = team_name.strip()

        if not normalized_team_name:
            raise InvalidTeamNameError(
                "Team name must not be empty."
            )

        if len(character_names) != self.TEAM_MEMBER_COUNT:
            raise InvalidTeamMemberCountError(
                f"A team must contain exactly "
                f"{self.TEAM_MEMBER_COUNT} characters."
            )

        normalized_character_names = [
            name.strip()
            for name in character_names
        ]

        if any(
            not name
            for name in normalized_character_names
        ):
            raise InvalidCharacterNameError(
                "Character name must not be empty."
            )

        normalized_keys = [
            name.casefold()
            for name in normalized_character_names
        ]

        if len(set(normalized_keys)) != self.TEAM_MEMBER_COUNT:
            raise DuplicateCharacterError(
                "The same character cannot be used twice."
            )

        with session_scope() as session:
            player_repository = PlayerRepository(session)
            character_repository = CharacterRepository(session)
            team_repository = TeamRepository(session)

            player = player_repository.get_by_discord_id(
                discord_id
            )

            if player is None:
                raise PlayerNotFoundError(
                    f"Discord ID {discord_id} was not found."
                )

            if not player.active:
                raise PlayerInactiveError(
                    f"Discord ID {discord_id} is inactive."
                )

            existing_team = (
                team_repository.get_by_player_and_name(
                    player_id=player.id,
                    team_name=normalized_team_name,
                )
            )

            if existing_team is not None:
                raise TeamAlreadyExistsError(
                    f"Team '{normalized_team_name}' "
                    "already exists."
                )

            normalized_memo = (
                memo.strip()
                if memo is not None and memo.strip()
                else None
            )

            team = team_repository.create(
                player_id=player.id,
                team_name=normalized_team_name,
                memo=normalized_memo,
            )

            for position, character_name in enumerate(
                normalized_character_names,
                start=1,
            ):
                character = (
                    character_repository.get_by_name(
                        character_name
                    )
                )

                if character is None:
                    character = (
                        character_repository.create(
                            character_name
                        )
                    )

                team_repository.add_member(
                    team=team,
                    character=character,
                    position=position,
                )

            # メンバー・Characterまで読み込んだTeamを
            # Serviceの外へ返す。
            created_team = team_repository.get_by_id(
                team.id
            )

            if created_team is None:
                raise RuntimeError(
                    "Created Team could not be loaded."
                )

            return created_team

    def list_active_teams(
        self,
        discord_id: str,
    ) -> list[Team]:
        """Playerの有効な編成一覧を取得する。"""

        with session_scope() as session:
            player_repository = PlayerRepository(session)
            team_repository = TeamRepository(session)

            player = player_repository.get_by_discord_id(
                discord_id
            )

            if player is None:
                raise PlayerNotFoundError(
                    f"Discord ID {discord_id} was not found."
                )

            return team_repository.list_active_by_player_id(
                player.id
            )

    def deactivate_team(
        self,
        discord_id: str,
        team_name: str,
    ) -> Team:
        """編成を無効化する。"""

        normalized_team_name = team_name.strip()

        if not normalized_team_name:
            raise InvalidTeamNameError(
                "Team name must not be empty."
            )

        with session_scope() as session:
            player_repository = PlayerRepository(session)
            team_repository = TeamRepository(session)

            player = player_repository.get_by_discord_id(
                discord_id
            )

            if player is None:
                raise PlayerNotFoundError(
                    f"Discord ID {discord_id} was not found."
                )

            team = team_repository.get_by_player_and_name(
                player_id=player.id,
                team_name=normalized_team_name,
            )

            if team is None:
                raise TeamNotFoundError(
                    f"Team '{normalized_team_name}' "
                    "was not found."
                )

            if not team.active:
                raise TeamAlreadyInactiveError(
                    f"Team '{normalized_team_name}' "
                    "is already inactive."
                )

            return team_repository.deactivate(team)