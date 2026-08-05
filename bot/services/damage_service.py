from bot.core.database import session_scope
from bot.exceptions import (
    ActiveRaidNotFoundError,
    BossNotFoundError,
    InvalidBossNumberError,
    InvalidDamageError,
    PlayerNotFoundError,
    TeamInactiveError,
    TeamNotFoundError,
)
from bot.models.boss import Boss
from bot.models.damage import DamageRecord
from bot.repositories import (
    BossRepository,
    DamageRepository,
    PlayerRepository,
    RaidRepository,
    TeamRepository,
)


class DamageService:
    """ダメージ登録に関するアプリケーション処理。"""

    BOSS_MIN_NUMBER = 1
    BOSS_MAX_NUMBER = 5

    def register_damage(
        self,
        discord_id: str,
        team_name: str,
        boss_no: int,
        damage: int,
        image_path: str | None = None,
        ocr_confidence: float | None = None,
    ) -> tuple[DamageRecord, Boss]:
        """
        DamageRecordを保存し、Boss残HPを更新する。

        Returns:
            DamageRecordと更新後Boss。
        """

        normalized_team_name = team_name.strip()

        if not normalized_team_name:
            raise TeamNotFoundError(
                "Team name must not be empty."
            )

        self._validate_boss_number(
            boss_no
        )

        if damage <= 0:
            raise InvalidDamageError(
                "Damage must be greater than zero."
            )

        if ocr_confidence is not None and not (
            0.0 <= ocr_confidence <= 1.0
        ):
            raise ValueError(
                "OCR confidence must be between 0 and 1."
            )

        with session_scope() as session:
            player_repository = PlayerRepository(session)
            team_repository = TeamRepository(session)
            raid_repository = RaidRepository(session)
            boss_repository = BossRepository(session)
            damage_repository = DamageRepository(session)

            player = player_repository.get_by_discord_id(
                discord_id
            )

            if player is None:
                raise PlayerNotFoundError(
                    f"Discord ID {discord_id} was not found."
                )

            team = team_repository.get_by_player_and_name(
                player_id=player.id,
                team_name=normalized_team_name,
            )

            if team is None:
                raise TeamNotFoundError(
                    f"Team '{normalized_team_name}' was not found."
                )

            if not team.active:
                raise TeamInactiveError(
                    f"Team '{normalized_team_name}' is inactive."
                )

            raid = raid_repository.get_active()

            if raid is None:
                raise ActiveRaidNotFoundError(
                    "Active Raid was not found."
                )

            boss = boss_repository.get_by_raid_and_number(
                raid_id=raid.id,
                boss_no=boss_no,
            )

            if boss is None:
                raise BossNotFoundError(
                    f"Boss {boss_no} was not found."
                )

            record = damage_repository.create(
                team_id=team.id,
                boss_id=boss.id,
                damage=damage,
                image_path=image_path,
                ocr_confidence=ocr_confidence,
            )

            new_hp = max(
                boss.current_hp - damage,
                0,
            )

            boss_repository.set_current_hp(
                boss=boss,
                current_hp=new_hp,
            )

            return record, boss

    def _validate_boss_number(
        self,
        boss_no: int,
    ) -> None:
        if not (
            self.BOSS_MIN_NUMBER
            <= boss_no
            <= self.BOSS_MAX_NUMBER
        ):
            raise InvalidBossNumberError(
                "Boss number must be between "
                f"{self.BOSS_MIN_NUMBER} and "
                f"{self.BOSS_MAX_NUMBER}."
            )