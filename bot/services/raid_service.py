from bot.core.database import session_scope
from bot.exceptions import (
    ActiveRaidNotFoundError,
    BossNotFoundError,
    InvalidBossHpError,
    InvalidBossNameError,
    InvalidBossNumberError,
    InvalidRaidNameError,
    RaidAlreadyExistsError,
    BossPhaseAlreadyExistsError,
    BossPhaseNotFoundError,
    InvalidPhaseNumberError,
)
from bot.models.boss import Boss
from bot.models.raid import Raid
from bot.repositories import (
    BossRepository,
    RaidRepository,
    BossPhaseRepository,
)

from bot.data.boss_master import (
    resolve_phase_no_by_name,
)

from bot.models.boss_phase import BossPhase


class RaidService:
    """Raid・Boss管理のアプリケーション処理。"""

    BOSS_MIN_NUMBER = 1
    BOSS_MAX_NUMBER = 5

    def create_raid(
        self,
        name: str,
    ) -> Raid:
        """新しいRaidを作成し、現在開催中にする。"""

        normalized_name = name.strip()

        if not normalized_name:
            raise InvalidRaidNameError(
                "Raid name must not be empty."
            )

        with session_scope() as session:
            raid_repository = RaidRepository(session)

            existing = raid_repository.get_by_name(
                normalized_name
            )

            if existing is not None:
                raise RaidAlreadyExistsError(
                    f"Raid '{normalized_name}' already exists."
                )

            # 新しいRaidを開始したら、
            # 以前のRaidは終了扱いにする。
            raid_repository.deactivate_all()

            return raid_repository.create(
                normalized_name
            )

    def get_active_raid(self) -> Raid:
        """現在開催中のRaidを取得する。"""

        with session_scope() as session:
            raid_repository = RaidRepository(session)

            raid = raid_repository.get_active()

            if raid is None:
                raise ActiveRaidNotFoundError(
                    "Active Raid was not found."
                )

            return raid

    def set_boss(
        self,
        boss_no: int,
        name: str,
        max_hp: int,
    ) -> Boss:
        """現在のRaidにBossを登録・更新する。"""

        self._validate_boss_number(
            boss_no
        )

        normalized_name = name.strip()

        if not normalized_name:
            raise InvalidBossNameError(
                "Boss name must not be empty."
            )

        if max_hp <= 0:
            raise InvalidBossHpError(
                "Boss HP must be greater than zero."
            )

        with session_scope() as session:
            raid_repository = RaidRepository(session)
            boss_repository = BossRepository(session)

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
                return boss_repository.create(
                    raid_id=raid.id,
                    boss_no=boss_no,
                    name=normalized_name,
                    max_hp=max_hp,
                )

            return boss_repository.update_definition(
                boss=boss,
                name=normalized_name,
                max_hp=max_hp,
            )

    def set_current_hp(
        self,
        boss_no: int,
        current_hp: int,
    ) -> Boss:
        """現在のBoss残HPを変更する。"""

        self._validate_boss_number(
            boss_no
        )

        if current_hp < 0:
            raise InvalidBossHpError(
                "Boss HP must not be negative."
            )

        with session_scope() as session:
            raid_repository = RaidRepository(session)
            boss_repository = BossRepository(session)

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

            if current_hp > boss.max_hp:
                raise InvalidBossHpError(
                    "Current HP cannot exceed max HP."
                )

            return boss_repository.set_current_hp(
                boss=boss,
                current_hp=current_hp,
            )

    def list_bosses(self) -> list[Boss]:
        """現在開催中RaidのBoss一覧を取得する。"""

        with session_scope() as session:
            raid_repository = RaidRepository(session)
            boss_repository = BossRepository(session)

            raid = raid_repository.get_active()

            if raid is None:
                raise ActiveRaidNotFoundError(
                    "Active Raid was not found."
                )

            return boss_repository.list_by_raid_id(
                raid.id
            )

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
    
    def set_boss_phase(
        self,
        boss_no: int,
        phase_no: int,
        max_hp: int,
    ) -> BossPhase:
        """BossのPhaseと最大HPを登録・更新する。"""

        self._validate_boss_number(
            boss_no
        )

        if phase_no <= 0:
            raise InvalidPhaseNumberError(
                "Phase number must be greater than zero."
            )

        if max_hp <= 0:
            raise InvalidBossHpError(
                "Boss HP must be greater than zero."
            )

        with session_scope() as session:
            raid_repository = RaidRepository(
                session
            )
            boss_repository = BossRepository(
                session
            )
            phase_repository = BossPhaseRepository(
                session
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

            same_hp_phase = (
                phase_repository.get_by_boss_and_max_hp(
                    boss_id=boss.id,
                    max_hp=max_hp,
                )
            )

            if (
                same_hp_phase is not None
                and same_hp_phase.phase_no != phase_no
            ):
                raise BossPhaseAlreadyExistsError(
                    f"Max HP {max_hp} is already assigned "
                    f"to Phase {same_hp_phase.phase_no}."
                )

            phase = (
                phase_repository.get_by_boss_and_phase(
                    boss_id=boss.id,
                    phase_no=phase_no,
                )
            )

            if phase is None:
                return phase_repository.create(
                    boss_id=boss.id,
                    phase_no=phase_no,
                    max_hp=max_hp,
                )

            return phase_repository.update_max_hp(
                phase=phase,
                max_hp=max_hp,
            )

    def resolve_boss_phase(
        self,
        boss_name: str,
        max_hp: int,
    ) -> BossPhase:
        """
        Boss名と最大HPからPhaseを判定する。

        Phase番号の判定には、
        DBのmax_hpではなく
        boss_master.pyを正式な情報源として使用する。

        OCRで

            残HP / 最大HP

        の "/" を認識できず、

            残HP最大HP

        のように数字が連結された場合は、
        右端からBoss Masterの最大HPと照合して
        最大HPを復元する。

        DBのBossPhaseは、
        boss_phase_idを取得するために使用する。
        """

        normalized_boss_name = (
            boss_name.strip()
        )

        if not normalized_boss_name:
            raise BossNotFoundError(
                "Boss name must not be empty."
            )

        if max_hp <= 0:
            raise InvalidBossHpError(
                "Boss HP must be greater than zero."
            )

        # --------------------------------
        # Boss MasterからPhase番号を判定
        #
        # まず通常の完全一致。
        # --------------------------------

        phase_no = resolve_phase_no_by_name(
            boss_name=normalized_boss_name,
            max_hp=max_hp,
        )

        resolved_max_hp = max_hp

        # --------------------------------
        # 完全一致しなかった場合
        #
        # OCRが
        #
        #   残HP / 最大HP
        #
        # の "/" を認識できず、
        #
        #   残HP最大HP
        #
        # と連結した可能性を調べる。
        # --------------------------------

        if phase_no is None:
            (
                phase_no,
                resolved_max_hp,
            ) = self._resolve_joined_hp(
                boss_name=normalized_boss_name,
                recognized_hp=max_hp,
            )

        if phase_no is None:
            raise BossPhaseNotFoundError(
                (
                    "Boss Masterに一致するPhaseが"
                    "見つかりませんでした: "
                    f"Boss='{normalized_boss_name}', "
                    f"Recognized HP={max_hp}"
                )
            )

        # --------------------------------
        # DBから対応するBossPhaseを取得
        # --------------------------------

        with session_scope() as session:
            raid_repository = RaidRepository(
                session
            )

            boss_repository = BossRepository(
                session
            )

            phase_repository = (
                BossPhaseRepository(
                    session
                )
            )

            raid = raid_repository.get_active()

            if raid is None:
                raise ActiveRaidNotFoundError(
                    "Active Raid was not found."
                )

            boss = (
                boss_repository.get_by_raid_and_name(
                    raid_id=raid.id,
                    name=normalized_boss_name,
                )
            )

            if boss is None:
                raise BossNotFoundError(
                    (
                        f"Boss '{normalized_boss_name}' "
                        "was not found in the active Raid."
                    )
                )

            phase = (
                phase_repository
                .get_by_boss_and_phase(
                    boss_id=boss.id,
                    phase_no=phase_no,
                )
            )

            if phase is None:
                raise BossPhaseNotFoundError(
                    (
                        "Boss MasterではPhaseが"
                        "判定できましたが、"
                        "DBに対応するBossPhaseが"
                        "存在しません: "
                        f"Boss='{boss.name}', "
                        f"Phase={phase_no}"
                    )
                )

            # Boss MasterとDBの最大HPが
            # 食い違っている場合は登録しない。
            if phase.max_hp != resolved_max_hp:
                raise BossPhaseNotFoundError(
                    (
                        "Boss MasterとDBの最大HPが"
                        "一致しません: "
                        f"Boss='{boss.name}', "
                        f"Phase={phase_no}, "
                        f"Master HP={resolved_max_hp}, "
                        f"DB HP={phase.max_hp}"
                    )
                )

            return phase

    def _resolve_joined_hp(
        self,
        *,
        boss_name: str,
        recognized_hp: int,
    ) -> tuple[int | None, int]:
        """
        OCRで残HPと最大HPが連結された値から、
        Boss Masterの最大HPを復元する。

        例:

            本来:
                85,123,456,789
                /
                150,841,813,600

            OCR:
                85123456789150841813600

        右端から1桁ずつ候補を伸ばし、
        Boss Masterのmax_hpと完全一致する候補を探す。

        複数候補が見つかった場合は、
        最も桁数の長い一致を採用する。
        """

        recognized_text = str(
            recognized_hp
        )

        matches: list[
            tuple[
                int,
                int,
                int,
            ]
        ] = []

        # --------------------------------
        # 右端から
        #
        # 1桁
        # 2桁
        # 3桁
        # ...
        #
        # と候補を伸ばす。
        # --------------------------------

        for digit_count in range(
            1,
            len(recognized_text),
        ):
            max_hp_text = (
                recognized_text[
                    -digit_count:
                ]
            )

            remaining_hp_text = (
                recognized_text[
                    :-digit_count
                ]
            )

            if not remaining_hp_text:
                continue

            # 先頭0を含む不自然な最大HP候補は
            # 対象外にする。
            if max_hp_text.startswith(
                "0"
            ):
                continue

            candidate_max_hp = int(
                max_hp_text
            )

            candidate_phase_no = (
                resolve_phase_no_by_name(
                    boss_name=boss_name,
                    max_hp=candidate_max_hp,
                )
            )

            # Boss Masterに存在しないHP。
            if candidate_phase_no is None:
                continue

            # --------------------------------
            # 左側が本当に残HPとして
            # 成立するか確認する。
            # --------------------------------

            remaining_hp = int(
                remaining_hp_text
            )

            if remaining_hp < 0:
                continue

            if (
                remaining_hp
                > candidate_max_hp
            ):
                continue

            matches.append(
                (
                    digit_count,
                    candidate_phase_no,
                    candidate_max_hp,
                )
            )

        if not matches:
            return (
                None,
                recognized_hp,
            )

        # --------------------------------
        # 万一複数のMaster HPが
        # 末尾一致した場合、
        # 最も長い完全一致を採用する。
        # --------------------------------

        (
            _,
            phase_no,
            resolved_max_hp,
        ) = max(
            matches,
            key=lambda item: item[0],
        )

        return (
            phase_no,
            resolved_max_hp,
        )

    def list_boss_phases(
        self,
        boss_no: int,
    ) -> list[BossPhase]:
        """BossのPhase一覧を取得する。"""

        self._validate_boss_number(
            boss_no
        )

        with session_scope() as session:
            raid_repository = RaidRepository(
                session
            )
            boss_repository = BossRepository(
                session
            )
            phase_repository = BossPhaseRepository(
                session
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

            return phase_repository.list_by_boss_id(
                boss.id
            )