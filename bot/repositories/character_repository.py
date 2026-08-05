from sqlalchemy import select
from sqlalchemy.orm import Session

from bot.models.character import Character


class CharacterRepository:
    """CharacterのDB操作を担当するRepository。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        name: str,
    ) -> Character:
        """Characterを新規作成する。"""

        character = Character(
            name=name,
        )

        self._session.add(character)
        self._session.flush()

        return character

    def get_by_id(
        self,
        character_id: int,
    ) -> Character | None:
        """Character IDから取得する。"""

        return self._session.get(
            Character,
            character_id,
        )

    def get_by_name(
        self,
        name: str,
    ) -> Character | None:
        """名前からCharacterを取得する。"""

        statement = select(Character).where(
            Character.name == name
        )

        return self._session.scalar(statement)

    def list_all(self) -> list[Character]:
        """Characterをすべて取得する。"""

        statement = (
            select(Character)
            .order_by(Character.name)
        )

        return list(
            self._session.scalars(statement).all()
        )