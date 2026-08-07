from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from bot.models.raid import Raid


class RaidProgressRepository:
    """Raid進行状態のDBアクセス。"""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

    def get_by_id(
        self,
        raid_id: int,
    ) -> Raid | None:
        return self.session.get(
            Raid,
            raid_id,
        )

    def get_active(
        self,
    ) -> Raid | None:
        return self.session.scalar(
            select(Raid)
            .where(
                Raid.active.is_(True)
            )
            .order_by(
                Raid.id.desc()
            )
        )

    def set_current_phase(
        self,
        raid: Raid,
        phase_no: int,
    ) -> None:
        raid.current_phase = phase_no

        self.session.flush()