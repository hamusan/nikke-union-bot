from sqlalchemy import select
from sqlalchemy.orm import Session

from bot.models.boss import Boss


class BossRepository:
    """BossのDB操作を担当するRepository。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        raid_id: int,
        boss_no: int,
        name: str,
        max_hp: int,
    ) -> Boss:
        boss = Boss(
            raid_id=raid_id,
            boss_no=boss_no,
            name=name,
            max_hp=max_hp,
            current_hp=max_hp,
        )

        self._session.add(boss)
        self._session.flush()

        return boss

    def get_by_raid_and_number(
        self,
        raid_id: int,
        boss_no: int,
    ) -> Boss | None:
        statement = select(Boss).where(
            Boss.raid_id == raid_id,
            Boss.boss_no == boss_no,
        )

        return self._session.scalar(statement)

    def list_by_raid_id(
        self,
        raid_id: int,
    ) -> list[Boss]:
        statement = (
            select(Boss)
            .where(
                Boss.raid_id == raid_id
            )
            .order_by(
                Boss.boss_no
            )
        )

        return list(
            self._session.scalars(statement).all()
        )

    def update_definition(
        self,
        boss: Boss,
        name: str,
        max_hp: int,
    ) -> Boss:
        boss.name = name
        boss.max_hp = max_hp
        boss.current_hp = max_hp

        self._session.flush()

        return boss

    def set_current_hp(
        self,
        boss: Boss,
        current_hp: int,
    ) -> Boss:
        boss.current_hp = current_hp

        self._session.flush()

        return boss

    def get_by_raid_and_name(
        self,
        raid_id: int,
        name: str,
    ) -> Boss | None:
        """Raid内のBossを名前から取得する。"""

        statement = select(Boss).where(
            Boss.raid_id == raid_id,
            Boss.name == name,
        )

        return self._session.scalar(
            statement
        )