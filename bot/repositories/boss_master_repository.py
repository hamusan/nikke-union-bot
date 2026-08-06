from sqlalchemy import (
    delete,
    select,
)
from sqlalchemy.orm import Session

from bot.models import (
    Boss,
    BossPhase,
    DamageRecord,
    Raid,
)


class BossMasterRepository:
    """
    Raid BossとBoss Master同期用の
    DB操作。
    """

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def get_active_raid(
        self,
    ) -> Raid | None:
        statement = (
            select(Raid)
            .where(
                Raid.active.is_(True)
            )
            .order_by(
                Raid.id.desc()
            )
        )

        return self._session.scalar(
            statement
        )

    def get_boss_by_slot(
        self,
        raid_id: int,
        boss_no: int,
    ) -> Boss | None:
        statement = select(
            Boss
        ).where(
            Boss.raid_id == raid_id,
            Boss.boss_no == boss_no,
        )

        return self._session.scalar(
            statement
        )

    def get_boss_by_key(
        self,
        raid_id: int,
        boss_key: str,
    ) -> Boss | None:
        statement = select(
            Boss
        ).where(
            Boss.raid_id == raid_id,
            Boss.boss_key == boss_key,
        )

        return self._session.scalar(
            statement
        )

    def has_damage_records(
        self,
        boss_id: int,
    ) -> bool:
        statement = (
            select(DamageRecord.id)
            .where(
                DamageRecord.boss_id
                == boss_id
            )
            .limit(1)
        )

        return (
            self._session.scalar(
                statement
            )
            is not None
        )

    def create_boss(
        self,
        raid_id: int,
        boss_no: int,
        boss_key: str,
        boss_name: str,
        legacy_hp: int,
    ) -> Boss:
        """
        Boss rowを作成する。

        max_hp/current_hpは旧仕様との
        互換性のためだけに設定する。
        新仕様では使用しない。
        """

        boss = Boss(
            raid_id=raid_id,
            boss_no=boss_no,
            boss_key=boss_key,
            name=boss_name,
            max_hp=legacy_hp,
            current_hp=legacy_hp,
        )

        self._session.add(
            boss
        )

        self._session.flush()

        return boss

    def update_boss(
        self,
        boss: Boss,
        boss_key: str,
        boss_name: str,
        legacy_hp: int,
    ) -> Boss:
        boss.boss_key = boss_key
        boss.name = boss_name

        # 旧列は残すがロジックでは使わない。
        boss.max_hp = legacy_hp
        boss.current_hp = legacy_hp

        self._session.flush()

        return boss

    def delete_boss_phases(
        self,
        boss_id: int,
    ) -> None:
        self._session.execute(
            delete(BossPhase)
            .where(
                BossPhase.boss_id
                == boss_id
            )
        )

        self._session.flush()

    def get_phase(
        self,
        boss_id: int,
        phase_no: int,
    ) -> BossPhase | None:
        statement = select(
            BossPhase
        ).where(
            BossPhase.boss_id == boss_id,
            BossPhase.phase_no == phase_no,
        )

        return self._session.scalar(
            statement
        )

    def upsert_phase(
        self,
        boss_id: int,
        phase_no: int,
        max_hp: int,
    ) -> BossPhase:
        phase = self.get_phase(
            boss_id=boss_id,
            phase_no=phase_no,
        )

        if phase is None:
            phase = BossPhase(
                boss_id=boss_id,
                phase_no=phase_no,
                max_hp=max_hp,
            )

            self._session.add(
                phase
            )

        else:
            phase.max_hp = max_hp

        self._session.flush()

        return phase
    def list_bosses_by_raid(
        self,
        raid_id: int,
    ) -> list[Boss]:
        """Raidに設定されているBossを番号順で取得する。"""

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
            self._session.scalars(
                statement
            ).all()
        )