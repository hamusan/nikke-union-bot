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
    """OCR解析済みDamageRecordの登録・更新処理。"""

    def register(
        self,
        team_id: int,
        boss_id: int,
        boss_phase_id: int,
        damage: int,
        image_path: str,
        image_sha256: str,
        ocr_confidence: float | None,
    ) -> tuple[DamageRecord, bool]:
        """
        OCR解析済みDamageを登録する。

        同じTeam・Boss・PhaseのRecordがあれば更新する。

        Returns:
            (record, created)

            created=True:
                新規登録

            created=False:
                既存DamageRecordを更新
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

            # 同じTeam・Boss・Phaseの
            # DamageRecordを先に探す。
            existing = (
                repository.get_by_team_boss_phase(
                    team_id=team_id,
                    boss_id=boss_id,
                    boss_phase_id=boss_phase_id,
                )
            )

            # 同じ画像が既に使われているか確認。
            duplicate_image = (
                repository.get_by_image_sha256(
                    normalized_hash
                )
            )

            # 同じ画像が存在していても、
            # 今回更新するRecord自身なら許可する。
            #
            # 別Recordが同じ画像を使用している場合だけ
            # 二重登録として拒否する。
            if duplicate_image is not None:
                if (
                    existing is None
                    or duplicate_image.id
                    != existing.id
                ):
                    raise DuplicateDamageImageError(
                        "このスクリーンショットは"
                        "別のDamageRecordで"
                        "既に使用されています。"
                    )

            # 同じTeam・Boss・Phaseなら更新。
            if existing is not None:
                record = repository.update_damage(
                    record=existing,
                    damage=damage,
                    image_path=image_path,
                    image_sha256=normalized_hash,
                    ocr_confidence=ocr_confidence,
                )

                return (
                    record,
                    False,
                )

            # 存在しなければ新規作成。
            record = repository.create(
                team_id=team_id,
                boss_id=boss_id,
                boss_phase_id=boss_phase_id,
                damage=damage,
                image_path=image_path,
                image_sha256=normalized_hash,
                ocr_confidence=ocr_confidence,
            )

            return (
                record,
                True,
            )