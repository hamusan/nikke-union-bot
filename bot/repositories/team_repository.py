from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from bot.models.character import Character
from bot.models.team import Team
from bot.models.team_member import TeamMember


class TeamRepository:
    """TeamのDB操作を担当するRepository。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        player_id: int,
        team_name: str,
        memo: str | None = None,
    ) -> Team:
        """Teamを新規作成する。"""

        team = Team(
            player_id=player_id,
            team_name=team_name,
            memo=memo,
        )

        self._session.add(team)
        self._session.flush()

        return team

    def get_by_id(
        self,
        team_id: int,
    ) -> Team | None:
        """Team IDから編成メンバー込みで取得する。"""

        statement = (
            select(Team)
            .options(
                selectinload(Team.members)
                .selectinload(TeamMember.character)
            )
            .where(Team.id == team_id)
        )

        return self._session.scalar(statement)

    def get_by_player_and_name(
        self,
        player_id: int,
        team_name: str,
    ) -> Team | None:
        """Player IDと編成名からTeamを取得する。"""

        statement = (
            select(Team)
            .where(
                Team.player_id == player_id,
                Team.team_name == team_name,
            )
        )

        return self._session.scalar(statement)

    def list_active_by_player_id(
        self,
        player_id: int,
    ) -> list[Team]:
        """Playerが所有する有効なTeamを取得する。"""

        statement = (
            select(Team)
            .options(
                selectinload(Team.members)
                .selectinload(TeamMember.character)
            )
            .where(
                Team.player_id == player_id,
                Team.active.is_(True),
            )
            .order_by(Team.team_name)
        )

        return list(
            self._session.scalars(statement).all()
        )

    def add_member(
        self,
        team: Team,
        character: Character,
        position: int,
    ) -> TeamMember:
        """TeamへCharacterを追加する。"""

        member = TeamMember(
            team_id=team.id,
            character_id=character.id,
            position=position,
        )

        self._session.add(member)
        self._session.flush()

        return member

    def deactivate(
        self,
        team: Team,
    ) -> Team:
        """Teamを無効化する。"""

        team.active = False
        self._session.flush()

        return team

    def reactivate(
        self,
        team: Team,
    ) -> Team:
        """Teamを再有効化する。"""

        team.active = True
        self._session.flush()

        return team