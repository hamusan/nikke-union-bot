from sqlalchemy import select
from sqlalchemy.orm import Session

from bot.models.player import Player


class PlayerRepository:
    """PlayerのDB操作を担当するRepository。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        discord_id: str,
        nickname: str,
    ) -> Player:
        """Playerを新規作成する。"""

        player = Player(
            discord_id=discord_id,
            nickname=nickname,
        )

        self._session.add(player)

        # INSERTを実行してIDなどを確定させる。
        # commitはsession_scope側で行う。
        self._session.flush()

        return player

    def get_by_id(
        self,
        player_id: int,
    ) -> Player | None:
        """Player IDから取得する。"""

        return self._session.get(
            Player,
            player_id,
        )

    def get_by_discord_id(
        self,
        discord_id: str,
    ) -> Player | None:
        """Discord IDからPlayerを取得する。"""

        statement = select(Player).where(
            Player.discord_id == discord_id
        )

        return self._session.scalar(statement)

    def list_active(self) -> list[Player]:
        """有効なPlayerをすべて取得する。"""

        statement = (
            select(Player)
            .where(Player.active.is_(True))
            .order_by(Player.nickname)
        )

        return list(
            self._session.scalars(statement).all()
        )