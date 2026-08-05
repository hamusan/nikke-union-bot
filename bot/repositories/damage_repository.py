from sqlalchemy import select
from sqlalchemy.orm import Session

from bot.models.damage import DamageRecord


class DamageRepository:
    """DamageRecordのDB操作を担当するRepository。"""

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
    ) -> DamageRecord:
        record = DamageRecord(
            team_id=team_id,
            boss_id=boss_id,
            damage=damage,
            image_path=image_path,
            ocr_confidence=ocr_confidence,
        )

        self._session.add(record)
        self._session.flush()

        return record

    def list_by_team_id(
        self,
        team_id: int,
    ) -> list[DamageRecord]:
        statement = (
            select(DamageRecord)
            .where(
                DamageRecord.team_id == team_id
            )
            .order_by(
                DamageRecord.created_at.desc()
            )
        )

        return list(
            self._session.scalars(statement).all()
        )

    def list_by_boss_id(
        self,
        boss_id: int,
    ) -> list[DamageRecord]:
        statement = (
            select(DamageRecord)
            .where(
                DamageRecord.boss_id == boss_id
            )
            .order_by(
                DamageRecord.created_at.desc()
            )
        )

        return list(
            self._session.scalars(statement).all()
        )