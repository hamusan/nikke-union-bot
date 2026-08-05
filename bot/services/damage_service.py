from bot.core.database import session_scope
from bot.exceptions import (
    ActiveRaidNotFoundError,
    BossNotFoundError,
    InvalidBossNumberError,
    InvalidDamageError,
    InvalidTeamNumberError,
    PlayerInactiveError,
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
        team_no: int,
        boss_no: int,
        damage: int,
        image_path: str | None = None,
        ocr_confidence: float | None = None,
    ) -> tuple[DamageRecord, Boss, int]:
        """DamageRecordを保存し、Boss残HPを更新する。"""

        if team_no <= 0:
            raise InvalidTeamNumberError(
                "Team number must be greater than zero."
            )

        if not (
            self.BOSS_MIN_NUMBER
            <= boss_no
            <= self.BOSS_MAX_NUMBER
        ):
            raise InvalidBossNumberError(
                "Boss number must be between 1 and 5."
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

            if not player.active:
                raise PlayerInactiveError(
                    f"Discord ID {discord_id} is inactive."
                )

            team = team_repository.get_by_player_and_number(
                player_id=player.id,
                team_no=team_no,
            )

            if team is None:
                raise TeamNotFoundError(
                    f"Team #{team_no} was not found."
                )

            if not team.active:
                raise TeamInactiveError(
                    f"Team #{team_no} is inactive."
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

            previous_hp = boss.current_hp

            record = damage_repository.create(
                team_id=team.id,
                boss_id=boss.id,
                damage=damage,
                image_path=image_path,
                ocr_confidence=ocr_confidence,
            )

            boss_repository.set_current_hp(
                boss=boss,
                current_hp=max(
                    previous_hp - damage,
                    0,
                ),
            )

            return record, boss, previous_hp