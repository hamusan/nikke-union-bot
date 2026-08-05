from sqlalchemy import select
from sqlalchemy.orm import Session

from bot.models.boss_phase import BossPhase


class BossPhaseRepository:
    """BossPhaseのDB操作を担当するRepository。"""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        boss_id: int,
        phase_no: int,
        max_hp: int,
    ) -> BossPhase:
        phase = BossPhase(
            boss_id=boss_id,
            phase_no=phase_no,
            max_hp=max_hp,
        )

        self._session.add(phase)
        self._session.flush()

        return phase

    def get_by_boss_and_phase(
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

    def get_by_boss_and_max_hp(
        self,
        boss_id: int,
        max_hp: int,
    ) -> BossPhase | None:
        statement = select(
            BossPhase
        ).where(
            BossPhase.boss_id == boss_id,
            BossPhase.max_hp == max_hp,
        )

        return self._session.scalar(
            statement
        )

    def list_by_boss_id(
        self,
        boss_id: int,
    ) -> list[BossPhase]:
        statement = (
            select(BossPhase)
            .where(
                BossPhase.boss_id == boss_id
            )
            .order_by(
                BossPhase.phase_no
            )
        )

        return list(
            self._session.scalars(
                statement
            ).all()
        )

    def update_max_hp(
        self,
        phase: BossPhase,
        max_hp: int,
    ) -> BossPhase:
        phase.max_hp = max_hp

        self._session.flush()

        return phase