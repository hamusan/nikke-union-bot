from bot.core.database import session_scope
from bot.exceptions import (
    DuplicateDamageImageError,
    InvalidDamageError,
)
from bot.models import DamageRecord
from bot.repositories.damage_repository import (
    DamageRepository,
)


class OcrDamageRegistrationService:
    """OCR解析済みDamageRecordの登録処理。"""

    def register(
        self,
        team_id: int,
        boss_id: int,
        boss_phase_id: int,
        damage: int,
        image_path: str,
        image_sha256: str,
        ocr_confidence: float | None,
    ) -> DamageRecord:
        """
        OCR解析済みデータをDamageRecordへ保存する。

        Boss.current_hpは変更しない。
        """

        if damage <= 0:
            raise InvalidDamageError(
                "Damageは1以上である必要があります。"
            )

        normalized_hash = (
            image_sha256
            .strip()
            .lower()
        )

        if len(normalized_hash) != 64:
            raise ValueError(
                "image_sha256 は64文字である必要があります。"
            )

        with session_scope() as session:
            repository = DamageRepository(
                session
            )

            existing = (
                repository.get_by_image_sha256(
                    normalized_hash
                )
            )

            if existing is not None:
                raise DuplicateDamageImageError(
                    "このスクリーンショットは"
                    "既に登録されています。"
                )

            record = repository.create(
                team_id=team_id,
                boss_id=boss_id,
                boss_phase_id=boss_phase_id,
                damage=damage,
                image_path=image_path,
                image_sha256=normalized_hash,
                ocr_confidence=ocr_confidence,
            )

            return record