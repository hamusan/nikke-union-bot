from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from bot.models.boss import Boss
from bot.models.boss_phase import (
    BossPhase,
)
from bot.models.raid import Raid
from bot.models.raid_boss_progress import (
    RaidBossProgress,
)


class RaidBossProgressRepository:
    """Boss残HPのDBアクセス。"""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

    def get_raid(
        self,
        raid_id: int,
    ) -> Raid | None:
        return self.session.get(
            Raid,
            raid_id,
        )

    def get_active_raid(
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

    def list_bosses(
        self,
        raid_id: int,
    ) -> list[Boss]:
        return list(
            self.session.scalars(
                select(Boss)
                .where(
                    Boss.raid_id
                    == raid_id
                )
                .order_by(
                    Boss.boss_no
                )
            ).all()
        )

    def get_boss_by_no(
        self,
        raid_id: int,
        boss_no: int,
    ) -> Boss | None:
        return self.session.scalar(
            select(Boss)
            .where(
                Boss.raid_id
                == raid_id
            )
            .where(
                Boss.boss_no
                == boss_no
            )
        )

    def get_phase(
        self,
        boss_id: int,
        phase_no: int,
    ) -> BossPhase | None:
        return self.session.scalar(
            select(BossPhase)
            .where(
                BossPhase.boss_id
                == boss_id
            )
            .where(
                BossPhase.phase_no
                == phase_no
            )
        )

    def get_progress(
        self,
        boss_phase_id: int,
    ) -> RaidBossProgress | None:
        return self.session.scalar(
            select(RaidBossProgress)
            .where(
                RaidBossProgress
                .boss_phase_id
                == boss_phase_id
            )
        )

    def get_or_create_progress(
        self,
        phase: BossPhase,
    ) -> RaidBossProgress:
        progress = self.get_progress(
            phase.id
        )

        if progress is not None:
            return progress

        progress = RaidBossProgress(
            boss_phase_id=phase.id,
            remaining_hp=phase.max_hp,
        )

        self.session.add(
            progress
        )

        self.session.flush()

        return progress

    def set_remaining_hp(
        self,
        progress: RaidBossProgress,
        remaining_hp: int,
    ) -> None:
        progress.remaining_hp = (
            remaining_hp
        )

        self.session.flush()