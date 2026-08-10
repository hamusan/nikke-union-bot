import asyncio
from dataclasses import dataclass, replace
import re
import unicodedata

import discord
from loguru import logger

from bot.exceptions import DuplicateDamageImageError
from bot.services import OcrDamageRegistrationService


@dataclass(frozen=True)
class PendingDamageRegistration:
    """確認待ちのDamage登録情報。"""

    # 元のDiscord投稿
    owner_id: int
    source_message_id: int

    # Raid
    raid_id: int

    # Player / Team
    player_id: int
    team_id: int
    team_no: int

    # Boss
    boss_id: int
    boss_name: str

    # Screenshotから判定したPhase
    boss_phase_id: int
    phase_no: int

    damage: int

    image_path: str
    image_sha256: str

    ocr_confidence: float | None


class ManualDamageModal(
    discord.ui.Modal,
    title="Damageを手動入力",
):
    """OCRで誤認識したDamageを手動修正する。"""

    damage_input = discord.ui.TextInput(
        label="Damage",
        placeholder="例: 19,361,444,152",
        required=True,
        max_length=30,
    )

    def __init__(
        self,
        confirmation_view: "DamageConfirmationView",
    ) -> None:
        super().__init__()

        self.confirmation_view = (
            confirmation_view
        )

        # 現在の解析結果を初期値として表示する。
        self.damage_input.default = (
            f"{confirmation_view.pending.damage:,}"
        )

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """入力されたDamageを確認画面へ反映する。"""

        await self.confirmation_view.apply_manual_damage(
            interaction=interaction,
            raw_damage=str(
                self.damage_input.value
            ),
        )


class DamageConfirmationView(
    discord.ui.View
):
    """DamageRecord登録確認UI。"""

    def __init__(
        self,
        pending: PendingDamageRegistration,
        base_content: str,
    ) -> None:
        super().__init__(
            timeout=120.0
        )

        self.pending = pending
        self.base_content = base_content

        self.registration_service = (
            OcrDamageRegistrationService()
        )

        self.message: discord.Message | None = None

        self._finished = False

        self._damage_manually_corrected = False

        self._lock = asyncio.Lock()

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """スクショ投稿者本人だけ操作可能にする。"""

        if (
            interaction.user.id
            == self.pending.owner_id
        ):
            return True

        await interaction.response.send_message(
            (
                "この操作はスクショの"
                "投稿者だけが実行できます。"
            ),
            ephemeral=True,
        )

        return False

    @discord.ui.button(
    label="登録する",
    style=discord.ButtonStyle.success,
    emoji="✅",
    )
    async def confirm_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        """
        DamageRecordへ正式登録する。

        この操作ではRaidAttackは登録しない。
        Boss HPやRaid Phaseも変更しない。
        """

        _ = button

        await interaction.response.defer()

        async with self._lock:
            if self._finished:
                await interaction.followup.send(
                    "この確認はすでに処理されています。",
                    ephemeral=True,
                )
                return

            try:
                (
                    record,
                    damage_record_created,
                ) = await asyncio.to_thread(
                    self.registration_service.register,
                    self.pending.team_id,
                    self.pending.boss_id,
                    self.pending.boss_phase_id,
                    self.pending.damage,
                    self.pending.image_path,
                    self.pending.image_sha256,
                    self.pending.ocr_confidence,
                )

            except DuplicateDamageImageError:
                self._finished = True

                self._disable_all_buttons()

                await interaction.edit_original_response(
                    content=(
                        self._current_content()
                        + "\n\n"
                        "⚠️ **この結果のスクリーンショットは"
                        "すでに登録されています。**"
                    ),
                    view=self,
                )

                self.stop()
                return

            except Exception:
                logger.exception(
                    (
                        "Damage registration failed: "
                        "owner_id={}, "
                        "team_id={}, "
                        "boss_id={}, "
                        "phase_id={}, "
                        "damage={}"
                    ),
                    self.pending.owner_id,
                    self.pending.team_id,
                    self.pending.boss_id,
                    self.pending.boss_phase_id,
                    self.pending.damage,
                )

                await interaction.followup.send(
                    (
                        "DamageRecordの登録中に"
                        "エラーが発生しました。"
                    ),
                    ephemeral=True,
                )
                return

            self._finished = True

            self._disable_all_buttons()

            if damage_record_created:
                result_message = (
                    "✅ **DamageRecordへ新規登録しました。**"
                )
            else:
                result_message = (
                    "🔄 **既存のDamageRecordを更新しました。**"
                )

            await interaction.edit_original_response(
                content=(
                    self._current_content()
                    + "\n\n"
                    + result_message
                    + "\n"
                    f"DamageRecord ID: `{record.id}`"
                    + "\n\n"
                    "ℹ️ この操作では実凸は登録されません。"
                ),
                view=self,
            )

            self.stop()

    @discord.ui.button(
        label="ダメージ手動入力",
        style=discord.ButtonStyle.secondary,
        emoji="✏️",
    )
    async def manual_damage_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        """Damageの手動修正フォームを表示する。"""

        if self._finished:
            await interaction.response.send_message(
                "この確認はすでに処理されています。",
                ephemeral=True,
            )
            return

        modal = ManualDamageModal(
            confirmation_view=self
        )

        await interaction.response.send_modal(
            modal
        )

    @discord.ui.button(
        label="キャンセル",
        style=discord.ButtonStyle.danger,
        emoji="✖️",
    )
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        """登録をキャンセルする。"""

        await interaction.response.defer()

        async with self._lock:
            if self._finished:
                await interaction.followup.send(
                    "この確認はすでに処理されています。",
                    ephemeral=True,
                )
                return

            self._finished = True

            self._disable_all_buttons()

            await interaction.edit_original_response(
                content=(
                    self._current_content()
                    + "\n\n"
                    "❌ **登録をキャンセルしました。**"
                ),
                view=self,
            )

            self.stop()

    async def apply_manual_damage(
        self,
        interaction: discord.Interaction,
        raw_damage: str,
    ) -> None:
        """手動入力されたDamageを解析結果へ反映する。"""

        if (
            interaction.user.id
            != self.pending.owner_id
        ):
            await interaction.response.send_message(
                (
                    "この操作はスクショの"
                    "投稿者だけが実行できます。"
                ),
                ephemeral=True,
            )
            return

        if self._finished:
            await interaction.response.send_message(
                "この確認はすでに処理されています。",
                ephemeral=True,
            )
            return

        damage = self._parse_manual_damage(
            raw_damage
        )

        if damage is None:
            await interaction.response.send_message(
                (
                    "Damageは正の整数で入力してください。\n"
                    "例: `19,361,444,152`"
                ),
                ephemeral=True,
            )
            return

        async with self._lock:
            if self._finished:
                await interaction.response.send_message(
                    "この確認はすでに処理されています。",
                    ephemeral=True,
                )
                return

            # frozen dataclassなのでreplace()で
            # 新しいPending情報へ差し替える。
            self.pending = replace(
                self.pending,
                damage=damage,

                # Damage自体はもうOCR値ではないため、
                # OCR confidenceは保存しない。
                ocr_confidence=None,
            )

            self._damage_manually_corrected = True

            await interaction.response.edit_message(
                content=self._current_content(),
                view=self,
            )

    def _parse_manual_damage(
        self,
        raw_damage: str,
    ) -> int | None:
        """
        手動入力Damageを整数へ変換する。

        以下を許可:
        19361444152
        19,361,444,152
        １９３６１４４４１５２
        """

        normalized = unicodedata.normalize(
            "NFKC",
            raw_damage,
        )

        cleaned = re.sub(
            r"[\s,_]",
            "",
            normalized,
        )

        if not cleaned.isdigit():
            return None

        try:
            damage = int(
                cleaned
            )

        except ValueError:
            return None

        if damage <= 0:
            return None

        return damage

    def _current_content(
        self,
    ) -> str:
        """現在のDamage値を反映した確認メッセージを生成する。"""

        updated = re.sub(
            r"Damage:\s*\*\*[\d,]+\*\*",
            (
                "Damage: "
                f"**{self.pending.damage:,}**"
            ),
            self.base_content,
            count=1,
        )

        if self._damage_manually_corrected:
            updated += (
                "\n\n"
                "✏️ **Damageは手動入力で修正されています。**"
            )

        return updated

    async def on_timeout(
        self,
    ) -> None:
        """2分間操作されなかった場合。"""

        if self._finished:
            return

        self._finished = True

        self._disable_all_buttons()

        if self.message is not None:
            try:
                await self.message.edit(
                    content=(
                        self._current_content()
                        + "\n\n"
                        "⌛ **確認時間が終了しました。"
                        "DamageRecordには登録していません。**"
                    ),
                    view=self,
                )

            except discord.HTTPException:
                logger.warning(
                    (
                        "Failed to update timed-out "
                        "damage confirmation."
                    )
                )

        self.stop()

    def _disable_all_buttons(
        self,
    ) -> None:
        """View内のボタンをすべて無効化する。"""

        for item in self.children:
            if isinstance(
                item,
                discord.ui.Button,
            ):
                item.disabled = True