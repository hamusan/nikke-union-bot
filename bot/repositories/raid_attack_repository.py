from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from bot.models.raid_attack import RaidAttack


class RaidAttackRepository:
    """RaidAttackのDBアクセス。"""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

    def get_by_id(
        self,
        attack_id: int,
    ) -> RaidAttack | None:
        return self.session.get(
            RaidAttack,
            attack_id,
        )

    def get_by_source_message_id(
        self,
        source_message_id: int,
    ) -> RaidAttack | None:
        return self.session.scalar(
            select(RaidAttack)
            .where(
                RaidAttack.source_message_id
                == source_message_id
            )
        )

    def get_by_image_sha256(
        self,
        image_sha256: str,
    ) -> RaidAttack | None:
        return self.session.scalar(
            select(RaidAttack)
            .where(
                RaidAttack.image_sha256
                == image_sha256
            )
        )

    def list_by_raid_id(
        self,
        raid_id: int,
    ) -> list[RaidAttack]:
        return list(
            self.session.scalars(
                select(RaidAttack)
                .where(
                    RaidAttack.raid_id
                    == raid_id
                )
                .order_by(
                    RaidAttack.id
                )
            ).all()
        )

    def list_by_raid_and_phase(
        self,
        raid_id: int,
        phase_no: int,
    ) -> list[RaidAttack]:
        return list(
            self.session.scalars(
                select(RaidAttack)
                .where(
                    RaidAttack.raid_id
                    == raid_id
                )
                .where(
                    RaidAttack.phase_no
                    == phase_no
                )
                .order_by(
                    RaidAttack.id
                )
            ).all()
        )

    def create(
        self,
        *,
        raid_id: int,
        phase_no: int,
        boss_id: int,
        player_id: int,
        team_id: int,
        damage: int,
        source_message_id: int | None = None,
        image_sha256: str | None = None,
    ) -> RaidAttack:
        attack = RaidAttack(
            raid_id=raid_id,
            phase_no=phase_no,
            boss_id=boss_id,
            player_id=player_id,
            team_id=team_id,
            damage=damage,
            source_message_id=source_message_id,
            image_sha256=image_sha256,
        )

        self.session.add(
            attack
        )

        self.session.flush()

        return attack