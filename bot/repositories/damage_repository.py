from sqlalchemy import select
from sqlalchemy.orm import Session

from bot.models import DamageRecord


class DamageRepository:
    """DamageRecordのDB操作。"""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        team_id: int,
        boss_id: int,
        damage: int,
        image_path: str | None = None,
        ocr_confidence: float | None = None,
        boss_phase_id: int | None = None,
        image_sha256: str | None = None,
    ) -> DamageRecord:
        """
        DamageRecordを作成する。

        既存コードとの互換性を保つため、
        boss_phase_idとimage_sha256は
        引数の後ろへ追加している。
        """

        record = DamageRecord(
            team_id=team_id,
            boss_id=boss_id,
            boss_phase_id=boss_phase_id,
            damage=damage,
            image_path=image_path,
            image_sha256=image_sha256,
            ocr_confidence=ocr_confidence,
        )

        self._session.add(
            record
        )

        self._session.flush()

        return record

    def get_by_id(
        self,
        record_id: int,
    ) -> DamageRecord | None:
        return self._session.get(
            DamageRecord,
            record_id,
        )

    def get_by_image_sha256(
        self,
        image_sha256: str,
    ) -> DamageRecord | None:
        statement = select(
            DamageRecord
        ).where(
            DamageRecord.image_sha256
            == image_sha256
        )

        return self._session.scalar(
            statement
        )

    def list_by_team_id(
        self,
        team_id: int,
    ) -> list[DamageRecord]:
        statement = (
            select(DamageRecord)
            .where(
                DamageRecord.team_id
                == team_id
            )
            .order_by(
                DamageRecord.created_at.desc()
            )
        )

        return list(
            self._session.scalars(
                statement
            ).all()
        )

    def list_by_boss_id(
        self,
        boss_id: int,
    ) -> list[DamageRecord]:
        statement = (
            select(DamageRecord)
            .where(
                DamageRecord.boss_id
                == boss_id
            )
            .order_by(
                DamageRecord.created_at.desc()
            )
        )

        return list(
            self._session.scalars(
                statement
            ).all()
        )
    def get_by_team_boss_phase(
        self,
        team_id: int,
        boss_id: int,
        boss_phase_id: int,
    ) -> DamageRecord | None:
        """同じTeam・Boss・PhaseのDamageRecordを取得する。"""

        statement = select(
            DamageRecord
        ).where(
            DamageRecord.team_id == team_id,
            DamageRecord.boss_id == boss_id,
            DamageRecord.boss_phase_id
            == boss_phase_id,
        )

        return self._session.scalar(
            statement
        )


    def update_damage(
        self,
        record: DamageRecord,
        damage: int,
        image_path: str,
        image_sha256: str,
        ocr_confidence: float | None,
    ) -> DamageRecord:
        """既存DamageRecordを最新結果で更新する。"""

        record.damage = damage
        record.image_path = image_path
        record.image_sha256 = image_sha256
        record.ocr_confidence = ocr_confidence

        self._session.flush()

        return record

    def list_by_raid_id(
        self,
        raid_id: int,
    ) -> list[DamageRecord]:
        """指定Raidの最適化対象DamageRecordを取得する。"""

        from sqlalchemy.orm import selectinload

        from bot.models import (
            Boss,
            Team,
        )

        statement = (
            select(DamageRecord)
            .join(
                Boss,
                DamageRecord.boss_id == Boss.id,
            )
            .where(
                Boss.raid_id == raid_id,
                DamageRecord.boss_phase_id.is_not(None),
            )
            .options(
                selectinload(
                    DamageRecord.team
                ).selectinload(
                    Team.members
                ),
                selectinload(
                    DamageRecord.boss_phase
                ),
            )
            .order_by(
                DamageRecord.team_id,
                DamageRecord.boss_id,
                DamageRecord.boss_phase_id,
            )
        )

        return list(
            self._session.scalars(
                statement
            ).all()
        )