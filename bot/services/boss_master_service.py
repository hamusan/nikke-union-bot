from dataclasses import dataclass

from bot.core.database import session_scope
from bot.data import (
    BossMaster,
    get_all_bosses,
    get_boss_by_key,
)
from bot.repositories.boss_master_repository import (
    BossMasterRepository,
)


@dataclass(frozen=True)
class RaidBossSyncResult:
    """Raid Boss設定結果。"""

    raid_id: int
    boss_id: int

    boss_no: int

    boss_key: str
    boss_name: str

    phase_count: int


@dataclass(frozen=True)
class RaidBossSlot:
    """Active RaidのBoss枠情報。"""

    raid_id: int

    boss_no: int

    boss_id: int | None
    boss_key: str | None
    boss_name: str | None

    master_registered: bool

    phase_hps: tuple[
        tuple[int, int],
        ...
    ]


class BossMasterService:
    """
    固定Boss Masterと
    Active RaidのBoss設定を管理するService。

    Boss名・Phase HPの正式な情報源は
    boss_master.py とする。
    """

    BOSS_MIN_NUMBER = 1
    BOSS_MAX_NUMBER = 5

    # ========================================================
    # Boss Master一覧
    # ========================================================

    def list_master_bosses(
        self,
    ) -> tuple[BossMaster, ...]:
        """選択可能な固定Boss一覧を取得する。"""

        return get_all_bosses()

    # ========================================================
    # Active Raid Boss一覧
    # ========================================================

    def list_active_raid_bosses(
        self,
    ) -> tuple[RaidBossSlot, ...]:
        """
        Active RaidのBoss #1～#5を取得する。

        DBにBoss rowが存在しない枠も
        空枠として返す。
        """

        with session_scope() as session:
            repository = BossMasterRepository(
                session
            )

            raid = repository.get_active_raid()

            if raid is None:
                raise ValueError(
                    "Active Raidがありません。"
                )

            bosses = (
                repository.list_bosses_by_raid(
                    raid_id=raid.id
                )
            )

            boss_by_no = {
                boss.boss_no: boss
                for boss in bosses
            }

            result: list[
                RaidBossSlot
            ] = []

            for boss_no in range(
                self.BOSS_MIN_NUMBER,
                self.BOSS_MAX_NUMBER + 1,
            ):
                boss = boss_by_no.get(
                    boss_no
                )

                # --------------------------------------------
                # Boss未設定
                # --------------------------------------------

                if boss is None:
                    result.append(
                        RaidBossSlot(
                            raid_id=raid.id,

                            boss_no=boss_no,

                            boss_id=None,
                            boss_key=None,
                            boss_name=None,

                            master_registered=False,

                            phase_hps=(),
                        )
                    )

                    continue

                # --------------------------------------------
                # Boss設定済み
                # --------------------------------------------

                master = None

                if boss.boss_key is not None:
                    master = get_boss_by_key(
                        boss.boss_key
                    )

                if master is None:
                    phase_hps: tuple[
                        tuple[int, int],
                        ...
                    ] = ()

                else:
                    phase_hps = tuple(
                        sorted(
                            master.phase_hps.items()
                        )
                    )

                result.append(
                    RaidBossSlot(
                        raid_id=raid.id,

                        boss_no=boss.boss_no,

                        boss_id=boss.id,
                        boss_key=boss.boss_key,
                        boss_name=boss.name,

                        master_registered=(
                            master is not None
                        ),

                        phase_hps=phase_hps,
                    )
                )

            return tuple(
                result
            )

    # ========================================================
    # Boss設定
    # ========================================================

    def set_active_raid_boss(
        self,
        boss_no: int,
        boss_key: str,
    ) -> RaidBossSyncResult:
        """
        Active RaidのBoss #1～#5へ
        Boss Masterを割り当てる。

        Boss名・Phase HPは
        Boss Masterから自動同期する。
        """

        self._validate_boss_number(
            boss_no
        )

        normalized_boss_key = (
            boss_key.strip()
        )

        if not normalized_boss_key:
            raise ValueError(
                "Boss keyが空です。"
            )

        master = get_boss_by_key(
            normalized_boss_key
        )

        if master is None:
            raise ValueError(
                (
                    "存在しないBoss keyです: "
                    f"{normalized_boss_key}"
                )
            )

        with session_scope() as session:
            repository = BossMasterRepository(
                session
            )

            raid = repository.get_active_raid()

            if raid is None:
                raise ValueError(
                    "Active Raidがありません。"
                )

            # --------------------------------------------
            # 同じBossを別のslotへ設定していないか
            # --------------------------------------------

            same_master_boss = (
                repository.get_boss_by_key(
                    raid_id=raid.id,
                    boss_key=master.key,
                )
            )

            if (
                same_master_boss is not None
                and same_master_boss.boss_no
                != boss_no
            ):
                raise ValueError(
                    (
                        f"{master.name} は既に "
                        f"Boss #{same_master_boss.boss_no} "
                        "へ設定されています。"
                    )
                )

            current = (
                repository.get_boss_by_slot(
                    raid_id=raid.id,
                    boss_no=boss_no,
                )
            )

            legacy_hp = (
                self._get_legacy_hp(
                    master
                )
            )

            # ============================================
            # Boss rowがまだ存在しない場合
            # ============================================

            if current is None:
                boss = repository.create_boss(
                    raid_id=raid.id,
                    boss_no=boss_no,
                    boss_key=master.key,
                    boss_name=master.name,
                    legacy_hp=legacy_hp,
                )

            # ============================================
            # 既存Boss rowがある場合
            # ============================================

            else:
                same_identity = (
                    current.boss_key
                    == master.key
                )

                # 旧DBではboss_keyがNULLでも、
                # nameが同じなら同一Bossとして扱う。
                legacy_same_identity = (
                    current.boss_key is None
                    and current.name == master.name
                )

                # ----------------------------------------
                # 本当に別Bossへ変更する場合
                # ----------------------------------------

                if (
                    not same_identity
                    and not legacy_same_identity
                ):
                    if (
                        repository.has_damage_records(
                            current.id
                        )
                    ):
                        raise ValueError(
                            (
                                f"Boss #{boss_no} には"
                                "既にDamageRecordがあります。"
                                "別のBossへ変更できません。"
                            )
                        )

                    # DamageRecordが無ければ
                    # 古いPhase情報を削除してよい。
                    repository.delete_boss_phases(
                        current.id
                    )

                boss = repository.update_boss(
                    boss=current,
                    boss_key=master.key,
                    boss_name=master.name,
                    legacy_hp=legacy_hp,
                )

            # ============================================
            # Boss Master → BossPhase DB同期
            # ============================================

            for (
                phase_no,
                max_hp,
            ) in sorted(
                master.phase_hps.items()
            ):
                repository.upsert_phase(
                    boss_id=boss.id,
                    phase_no=phase_no,
                    max_hp=max_hp,
                )

            return RaidBossSyncResult(
                raid_id=raid.id,
                boss_id=boss.id,

                boss_no=boss_no,

                boss_key=master.key,
                boss_name=master.name,

                phase_count=len(
                    master.phase_hps
                ),
            )

    # ========================================================
    # Validation
    # ========================================================

    def _validate_boss_number(
        self,
        boss_no: int,
    ) -> None:
        """Boss番号を検証する。"""

        if (
            boss_no
            < self.BOSS_MIN_NUMBER
            or boss_no
            > self.BOSS_MAX_NUMBER
        ):
            raise ValueError(
                (
                    "boss_noは"
                    f"{self.BOSS_MIN_NUMBER}～"
                    f"{self.BOSS_MAX_NUMBER}"
                    "で指定してください。"
                )
            )

    # ========================================================
    # Legacy compatibility
    # ========================================================

    def _get_legacy_hp(
        self,
        master: BossMaster,
    ) -> int:
        """
        旧Boss.max_hp/current_hp列へ
        入れる互換用HP。

        新しいロジックでは、
        Phase HPの正式な情報源として
        この値を使用しない。
        """

        if not master.phase_hps:
            raise ValueError(
                (
                    "Boss MasterにPhase情報が"
                    "ありません: "
                    f"{master.key}"
                )
            )

        first_phase_no = min(
            master.phase_hps
        )

        return master.phase_hps[
            first_phase_no
        ]