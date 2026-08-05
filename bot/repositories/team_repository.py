from sqlalchemy import func, select
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
        team_no: int,
        memo: str | None = None,
        team_name: str | None = None,
    ) -> Team:
        """Teamを新規作成する。"""

        team = Team(
            player_id=player_id,
            team_no=team_no,
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
            .where(
                Team.id == team_id
            )
        )

        return self._session.scalar(statement)

    def get_by_player_and_number(
        self,
        player_id: int,
        team_no: int,
    ) -> Team | None:
        """Player IDと編成番号からTeamを取得する。"""

        statement = (
            select(Team)
            .options(
                selectinload(Team.members)
                .selectinload(TeamMember.character)
            )
            .where(
                Team.player_id == player_id,
                Team.team_no == team_no,
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
            .order_by(
                Team.team_no
            )
        )

        return list(
            self._session.scalars(statement).all()
        )

    def get_next_team_number(
        self,
        player_id: int,
    ) -> int:
        """Playerの次の編成番号を取得する。"""

        statement = (
            select(
                func.max(Team.team_no)
            )
            .where(
                Team.player_id == player_id
            )
        )

        current_max = self._session.scalar(
            statement
        )

        return (current_max or 0) + 1

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