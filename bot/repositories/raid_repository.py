from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from bot.models.raid import Raid


class RaidRepository:
    """RaidのDB操作を担当するRepository。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        name: str,
    ) -> Raid:
        raid = Raid(
            name=name,
            active=True,
        )

        self._session.add(raid)
        self._session.flush()

        return raid

    def get_by_name(
        self,
        name: str,
    ) -> Raid | None:
        statement = select(Raid).where(
            Raid.name == name
        )

        return self._session.scalar(statement)

    def get_active(self) -> Raid | None:
        statement = (
            select(Raid)
            .options(
                selectinload(Raid.bosses)
            )
            .where(
                Raid.active.is_(True)
            )
        )

        return self._session.scalar(statement)

    def deactivate_all(self) -> None:
        statement = (
            update(Raid)
            .where(Raid.active.is_(True))
            .values(active=False)
        )

        self._session.execute(statement)
        self._session.flush()