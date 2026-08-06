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