from __future__ import annotations

import asyncio

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from bot.services.attack_overview_service import (
    AttackOverviewResult,
    AttackOverviewService,
    AttackTeamOverview,
)
from bot.services.raid_attack_cancellation_coordinator_service import (
    RaidAttackCancellationCoordinatorService,
)
from bot.services.attack_candidate_service import (
    AttackDamageCandidate,
    AttackCandidateService,
)
from bot.services.raid_attack_coordinator_service import (
    RaidAttackCoordinatorService,
)


class AttackTeamActionButton(
    discord.ui.Button
):
    """各Teamの実凸操作ボタン。"""

    def __init__(
        self,
        *,
        team: AttackTeamOverview,
        action: str,
        row: int,
    ) -> None:
        self.team_id = team.team_id
        self.action = action

        if action == "attack":
            super().__init__(
                label="実凸",
                emoji="⚔️",
                style=(
                    discord.ButtonStyle.success
                ),
                disabled=team.attacked,
                row=row,
            )

        elif action == "cancel":
            super().__init__(
                label="実凸取り消し",
                emoji="↩️",
                style=(
                    discord.ButtonStyle.danger
                ),
                disabled=not team.attacked,
                row=row,
            )

        else:
            raise ValueError(
                f"Unknown action: {action}"
            )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        view = self.view

        if not isinstance(
            view,
            AttackOverviewView,
        ):
            return

        if self.action == "attack":
            await view.handle_attack(
                interaction=interaction,
                team_id=self.team_id,
            )
            return

        await view.handle_cancel(
            interaction=interaction,
            team_id=self.team_id,
        )


class AttackPageButton(
    discord.ui.Button
):
    """ページ移動ボタン。"""

    def __init__(
        self,
        *,
        direction: int,
        disabled: bool,
    ) -> None:
        self.direction = direction

        if direction < 0:
            label = "前へ"
            emoji = "◀️"
        else:
            label = "次へ"
            emoji = "▶️"

        super().__init__(
            label=label,
            emoji=emoji,
            style=(
                discord.ButtonStyle.secondary
            ),
            disabled=disabled,
            row=4,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        view = self.view

        if not isinstance(
            view,
            AttackOverviewView,
        ):
            return

        await view.change_page(
            interaction=interaction,
            direction=self.direction,
        )

class AttackCandidateSelect(
    discord.ui.Select
):
    """複数のDamageRecordから実凸先を選択する。"""

    def __init__(
        self,
        candidates: tuple[
            AttackDamageCandidate,
            ...
        ],
    ) -> None:
        options: list[
            discord.SelectOption
        ] = []

        for candidate in candidates:
            label = (
                f"Boss #{candidate.boss_no} "
                f"{candidate.boss_name}"
            )

            description = (
                f"Damage {candidate.damage:,} "
                f"| HP {candidate.boss_remaining_hp:,}"
            )

            options.append(
                discord.SelectOption(
                    label=label[:100],
                    description=(
                        description[:100]
                    ),
                    value=str(
                        candidate.damage_record_id
                    ),
                    emoji="⚔️",
                )
            )

        super().__init__(
            placeholder=(
                "実凸するBoss / Damageを選択"
            ),
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        view = self.view

        if not isinstance(
            view,
            AttackCandidateSelectView,
        ):
            return

        await interaction.response.defer()

        try:
            damage_record_id = int(
                self.values[0]
            )

        except (
            ValueError,
            IndexError,
        ):
            await interaction.followup.send(
                (
                    "DamageRecordの選択値が"
                    "不正です。"
                ),
                ephemeral=True,
            )
            return

        success = (
            await view.parent_view
            .execute_attack_candidate(
                interaction=interaction,
                team_id=view.team_id,
                damage_record_id=(
                    damage_record_id
                ),
            )
        )

        if not success:
            return

        # 二重選択防止
        self.disabled = True

        try:
            await interaction.edit_original_response(
                content=(
                    "✅ 実凸を登録しました。"
                ),
                view=view,
            )

        except discord.HTTPException:
            pass

        view.stop()


class AttackCandidateSelectView(
    discord.ui.View
):
    """実凸候補選択用の一時View。"""

    def __init__(
        self,
        *,
        parent_view: "AttackOverviewView",
        team_id: int,
        candidates: tuple[
            AttackDamageCandidate,
            ...
        ],
    ) -> None:
        super().__init__(
            timeout=120.0
        )

        self.parent_view = (
            parent_view
        )

        self.team_id = (
            team_id
        )

        self.add_item(
            AttackCandidateSelect(
                candidates
            )
        )

class AttackOverviewView(
    discord.ui.View
):
    """
    /attack 実凸管理画面。

    Discordは最大5行なので、

    row 0: Team 1
    row 1: Team 2
    row 2: Team 3
    row 3: Team 4
    row 4: 前へ / 次へ

    とする。
    """

    PAGE_SIZE = 4

    def __init__(
        self,
        result: AttackOverviewResult,
    ) -> None:
        super().__init__(
            timeout=900.0
        )

        self.result = result
        self.page = 0

        self.message: (
            discord.Message
            | discord.WebhookMessage
            | None
        ) = None

        self.overview_service = (
            AttackOverviewService()
        )

        self.cancellation_service = (
            RaidAttackCancellationCoordinatorService()
        )
        self.candidate_service = (
            AttackCandidateService()
        )

        self.raid_attack_service = (
            RaidAttackCoordinatorService()
        )

        self._lock = asyncio.Lock()

        self._rebuild_items()

    @property
    def page_count(
        self,
    ) -> int:
        count = len(
            self.result.teams
        )

        return max(
            1,
            (
                count
                + self.PAGE_SIZE
                - 1
            )
            // self.PAGE_SIZE,
        )

    def get_page_teams(
        self,
    ) -> tuple[
        AttackTeamOverview,
        ...
    ]:
        start = (
            self.page
            * self.PAGE_SIZE
        )

        end = (
            start
            + self.PAGE_SIZE
        )

        return self.result.teams[
            start:end
        ]

    def _clamp_page(
        self,
    ) -> None:
        self.page = max(
            0,
            min(
                self.page,
                self.page_count - 1,
            ),
        )

    def _rebuild_items(
        self,
    ) -> None:
        """現在ページに合わせてButtonを再生成する。"""

        self.clear_items()

        self._clamp_page()

        for row, team in enumerate(
            self.get_page_teams()
        ):
            self.add_item(
                AttackTeamActionButton(
                    team=team,
                    action="attack",
                    row=row,
                )
            )

            self.add_item(
                AttackTeamActionButton(
                    team=team,
                    action="cancel",
                    row=row,
                )
            )

        self.add_item(
            AttackPageButton(
                direction=-1,
                disabled=(
                    self.page <= 0
                ),
            )
        )

        self.add_item(
            AttackPageButton(
                direction=1,
                disabled=(
                    self.page
                    >= self.page_count - 1
                ),
            )
        )

    def build_embed(
        self,
    ) -> discord.Embed:
        """現在ページのEmbedを作る。"""

        embed = discord.Embed(
            title="⚔️ 実凸管理",
            description=(
                f"Raid: **{self.result.raid_name}**\n"
                f"現在Phase: "
                f"**{self.result.current_phase}**\n"
                f"対象: **{self.result.target}**\n"
                f"ページ: "
                f"**{self.page + 1}"
                f" / {self.page_count}**"
            ),
        )

        page_teams = (
            self.get_page_teams()
        )

        if not page_teams:
            embed.add_field(
                name="編成なし",
                value=(
                    "表示できる有効な編成が"
                    "ありません。"
                ),
                inline=False,
            )

            return embed

        for team in page_teams:
            self._add_team_field(
                embed=embed,
                team=team,
            )

        return embed

    def _add_team_field(
        self,
        *,
        embed: discord.Embed,
        team: AttackTeamOverview,
    ) -> None:
        """1編成をEmbedへ追加する。"""

        if team.attacked:
            status = (
                "✅ **実凸済み**"
            )

            attack_info = (
                "\nRaidAttack ID: "
                f"`{team.raid_attack_id}`"
            )
        else:
            status = (
                "⬜ **未凸**"
            )

            attack_info = ""

        characters = " / ".join(
            team.character_names
        )

        if not characters:
            characters = (
                "キャラクター情報なし"
            )

        team_title = (
            f"{team.player_name} "
            f"/ Team #{team.team_no}"
        )

        if team.team_name:
            team_title += (
                f" - {team.team_name}"
            )

        embed.add_field(
            name=team_title,
            value=(
                f"{characters}\n"
                f"{status}"
                f"{attack_info}"
            ),
            inline=False,
        )

    def _find_team(
        self,
        team_id: int,
    ) -> AttackTeamOverview | None:
        for team in self.result.teams:
            if team.team_id == team_id:
                return team

        return None

    async def _refresh(
        self,
    ) -> None:
        """
        DBから最新状態を取得する。

        実凸/取消後は必ずこれを行う。
        """

        self.result = (
            await asyncio.to_thread(
                self.overview_service.build,
                self.result.target,
            )
        )

        self._clamp_page()
        self._rebuild_items()

    async def change_page(
        self,
        *,
        interaction: discord.Interaction,
        direction: int,
    ) -> None:
        """前/次ページへ移動する。"""

        self.page += direction

        self._clamp_page()
        self._rebuild_items()

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

    async def handle_attack(
        self,
        *,
        interaction: discord.Interaction,
        team_id: int,
    ) -> None:
        """
        実凸ボタン。

        0候補:
            スクショ登録を案内

        1候補:
            即RaidAttack登録

        複数候補:
            Selectを表示
        """

        await interaction.response.defer()

        try:
            result = await asyncio.to_thread(
                self.candidate_service
                .get_for_team,
                team_id,
            )

        except Exception as error:
            logger.error(
                (
                    "Failed to load "
                    "attack candidates: "
                    "team_id={}, error={!r}"
                ),
                team_id,
                error,
            )

            await interaction.followup.send(
                (
                    "⚠️ 実凸候補の取得中に"
                    "エラーが発生しました。"
                ),
                ephemeral=True,
            )
            return

        # --------------------------------
        # すでに実凸済み
        # --------------------------------

        if result.attacked:
            await self._refresh()

            await self._edit_management_message()

            await interaction.followup.send(
                (
                    "⚠️ この編成はすでに"
                    "実凸済みです。\n"
                    "RaidAttack ID: "
                    f"`{result.active_raid_attack_id}`"
                ),
                ephemeral=True,
            )
            return

        # --------------------------------
        # DamageRecordなし
        # --------------------------------

        if not result.candidates:
            await interaction.followup.send(
                (
                    "⚠️ **現在Phaseで使用できる"
                    "DamageRecordがありません。**\n\n"
                    "先にこの編成の結果スクショを"
                    "登録してください。"
                ),
                ephemeral=True,
            )
            return

        # --------------------------------
        # 候補1件
        # → 即実凸
        # --------------------------------

        if len(
            result.candidates
        ) == 1:
            candidate = (
                result.candidates[0]
            )

            await self.execute_attack_candidate(
                interaction=interaction,
                team_id=team_id,
                damage_record_id=(
                    candidate.damage_record_id
                ),
            )

            return

        # --------------------------------
        # 候補複数
        # → Select
        # --------------------------------

        select_view = (
            AttackCandidateSelectView(
                parent_view=self,
                team_id=team_id,
                candidates=(
                    result.candidates
                ),
            )
        )

        lines = [
            (
                f"**{candidate.boss_name}** "
                f"/ Damage "
                f"**{candidate.damage:,}**"
            )
            for candidate
            in result.candidates
        ]

        await interaction.followup.send(
            (
                "⚔️ **実凸するBossを"
                "選択してください。**\n\n"
                + "\n".join(lines)
            ),
            view=select_view,
            ephemeral=True,
        )

    async def execute_attack_candidate(
        self,
        *,
        interaction: discord.Interaction,
        team_id: int,
        damage_record_id: int,
    ) -> bool:
        """
        DamageRecordを再確認して
        実際にRaidAttackを登録する。

        Select表示後にPhaseが変わった場合なども
        ここで再検証する。
        """

        async with self._lock:
            try:
                # ----------------------------
                # 最新候補を再取得
                # ----------------------------

                result = await asyncio.to_thread(
                    self.candidate_service
                    .get_for_team,
                    team_id,
                )

                if result.attacked:
                    await self._refresh()
                    await self._edit_management_message()

                    await interaction.followup.send(
                        (
                            "⚠️ この編成はすでに"
                            "実凸済みです。\n"
                            "RaidAttack ID: "
                            f"`{result.active_raid_attack_id}`"
                        ),
                        ephemeral=True,
                    )

                    return False

                candidate = next(
                    (
                        item
                        for item
                        in result.candidates
                        if (
                            item.damage_record_id
                            == damage_record_id
                        )
                    ),
                    None,
                )

                # ----------------------------
                # Select表示後に
                # Phase/Boss状態などが変わった
                # ----------------------------

                if candidate is None:
                    await self._refresh()
                    await self._edit_management_message()

                    await interaction.followup.send(
                        (
                            "⚠️ 選択したDamageRecordは"
                            "現在のRaid状態では"
                            "使用できなくなりました。\n"
                            "もう一度 `⚔️ 実凸` を"
                            "押してください。"
                        ),
                        ephemeral=True,
                    )

                    return False

                # ----------------------------
                # RaidAttack
                #
                # コマンド登録なので
                # screenshot由来のHash等は
                # 使用しない。
                # ----------------------------

                raid_result = (
                    await asyncio.to_thread(
                        self.raid_attack_service
                        .record_attack,

                        raid_id=(
                            candidate.raid_id
                        ),

                        boss_id=(
                            candidate.boss_id
                        ),

                        player_id=(
                            candidate.player_id
                        ),

                        team_id=(
                            candidate.team_id
                        ),

                        damage=(
                            candidate.damage
                        ),

                        source_message_id=None,
                        image_sha256=None,

                        expected_phase_no=(
                            candidate.phase_no
                        ),
                    )
                )

                attack_result = (
                    raid_result.attack
                )

                # ----------------------------
                # 一覧を最新状態へ
                # ----------------------------

                await self._refresh()
                await self._edit_management_message()

                # ----------------------------
                # 結果メッセージ
                # ----------------------------

                lines = [
                    "✅ **実凸を登録しました。**",
                    "",
                    (
                        "RaidAttack ID: "
                        f"`{attack_result.attack.attack_id}`"
                    ),
                    (
                        "Boss: "
                        f"**#{candidate.boss_no} "
                        f"{candidate.boss_name}**"
                    ),
                    (
                        "Damage: "
                        f"**{candidate.damage:,}**"
                    ),
                ]

                if (
                    attack_result
                    .previous_remaining_hp
                    is not None
                    and attack_result
                    .remaining_hp
                    is not None
                ):
                    lines.append(
                        (
                            "Boss HP: "
                            f"**{attack_result.previous_remaining_hp:,}**"
                            " → "
                            f"**{attack_result.remaining_hp:,}**"
                        )
                    )

                if (
                    attack_result.applied_damage
                    != candidate.damage
                ):
                    lines.append(
                        (
                            "有効Damage: "
                            f"**{attack_result.applied_damage:,}**"
                        )
                    )

                if attack_result.defeated:
                    lines.append(
                        "💥 **Boss撃破**"
                    )

                lines.append(
                    (
                        "現在Phase: "
                        f"**{self.result.current_phase}**"
                    )
                )

                await interaction.followup.send(
                    "\n".join(lines),
                    ephemeral=True,
                )

                return True

            except ValueError as error:
                # Team二重凸やPhase変更など
                # Service側Validation
                await self._refresh()

                await self._edit_management_message()

                await interaction.followup.send(
                    f"⚠️ {error}",
                    ephemeral=True,
                )

                return False

            except Exception as error:
                logger.error(
                    (
                        "RaidAttack registration "
                        "failed: "
                        "team_id={}, "
                        "damage_record_id={}, "
                        "error={!r}"
                    ),
                    team_id,
                    damage_record_id,
                    error,
                )

                try:
                    await self._refresh()
                    await self._edit_management_message()

                except Exception:
                    pass

                await interaction.followup.send(
                    (
                        "実凸登録中に"
                        "エラーが発生しました。"
                    ),
                    ephemeral=True,
                )

                return False

    async def _edit_management_message(
        self,
    ) -> None:
        """実凸管理の元メッセージを更新する。"""

        if self.message is None:
            return

        try:
            await self.message.edit(
                embed=self.build_embed(),
                view=self,
            )

        except discord.NotFound:
            pass

        except discord.HTTPException:
            logger.warning(
                (
                    "Failed to update "
                    "attack management message."
                )
            )

    async def handle_cancel(
        self,
        *,
        interaction: discord.Interaction,
        team_id: int,
    ) -> None:
        """
        実凸を取り消し、
        Raid HP・Phaseを再構築する。
        """

        await interaction.response.defer()

        async with self._lock:
            try:
                # ----------------------------
                # 操作直前に最新状態を取得
                # ----------------------------

                await self._refresh()

                team = self._find_team(
                    team_id
                )

                if team is None:
                    await interaction.followup.send(
                        (
                            "対象の編成が"
                            "見つかりません。"
                        ),
                        ephemeral=True,
                    )
                    return

                raid_attack_id = (
                    team.raid_attack_id
                )

                # 他画面等からすでに
                # 取消されていた場合
                if raid_attack_id is None:
                    await interaction.edit_original_response(
                        embed=self.build_embed(),
                        view=self,
                    )

                    await interaction.followup.send(
                        (
                            "↩️ この編成はすでに"
                            "未凸状態です。"
                        ),
                        ephemeral=True,
                    )
                    return

                # ----------------------------
                # Cancellation + Raid rebuild
                # ----------------------------

                result = await asyncio.to_thread(
                    self.cancellation_service
                    .cancel_attack,

                    raid_attack_id=(
                        raid_attack_id
                    ),

                    cancelled_by_discord_id=(
                        str(
                            interaction.user.id
                        )
                    ),

                    reason=(
                        "Discord /attack "
                        "cancellation button"
                    ),
                )

                # ----------------------------
                # 取消後の最新状態へ更新
                # ----------------------------

                await self._refresh()

                await interaction.edit_original_response(
                    embed=self.build_embed(),
                    view=self,
                )

                cancellation = (
                    result.cancellation
                )

                rebuild = (
                    result.rebuild
                )

                if (
                    cancellation
                    .already_cancelled
                ):
                    headline = (
                        "↩️ **この実凸は"
                        "すでに取り消し済みでした。**"
                    )
                else:
                    headline = (
                        "✅ **実凸を"
                        "取り消しました。**"
                    )

                await interaction.followup.send(
                    (
                        f"{headline}\n\n"
                        "RaidAttack ID: "
                        f"`{raid_attack_id}`\n"
                        "Damage: "
                        f"**{cancellation.damage:,}**\n"
                        "現在Phase: "
                        f"**{rebuild.current_phase}**\n"
                        "有効実凸数: "
                        f"**{rebuild.active_attack_count}**"
                    ),
                    ephemeral=True,
                )

            except Exception as error:
                logger.error(
                    (
                        "RaidAttack cancellation "
                        "failed: "
                        "team_id={}, error={!r}"
                    ),
                    team_id,
                    error,
                )

                try:
                    await self._refresh()

                    await interaction.edit_original_response(
                        embed=self.build_embed(),
                        view=self,
                    )

                except Exception:
                    pass

                await interaction.followup.send(
                    (
                        "実凸取り消し中に"
                        "エラーが発生しました。"
                    ),
                    ephemeral=True,
                )

    async def on_timeout(
        self,
    ) -> None:
        """15分後に全ボタンを無効化する。"""

        for item in self.children:
            if isinstance(
                item,
                discord.ui.Button,
            ):
                item.disabled = True

        if self.message is None:
            return

        try:
            await self.message.edit(
                view=self
            )

        except discord.HTTPException:
            pass


class AttackCog(
    commands.Cog
):
    """実凸管理Discord UI。"""

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:
        self.bot = bot

        self.overview_service = (
            AttackOverviewService()
        )

    @app_commands.command(
        name="attack",
        description=(
            "実凸管理用の編成一覧を表示します"
        ),
    )
    @app_commands.describe(
        target=(
            "All またはプレイヤー名"
        ),
    )
    async def attack(
        self,
        interaction: discord.Interaction,
        target: str,
    ) -> None:
        """
        /attack target:All

        または

        /attack target:プレイヤー名
        """

        await interaction.response.defer()

        try:
            result = await asyncio.to_thread(
                self.overview_service.build,
                target,
            )

        except ValueError as error:
            await interaction.followup.send(
                f"⚠️ {error}",
                ephemeral=True,
            )
            return

        except RuntimeError as error:
            logger.error(
                (
                    "Attack overview "
                    "data inconsistency: "
                    "target={}, error={!r}"
                ),
                target,
                error,
            )

            await interaction.followup.send(
                (
                    "⚠️ 実凸データに"
                    "不整合が見つかりました。\n"
                    f"`{error}`"
                ),
                ephemeral=True,
            )
            return

        except Exception as error:
            logger.error(
                (
                    "Failed to build "
                    "attack overview: "
                    "target={}, error={!r}"
                ),
                target,
                error,
            )

            await interaction.followup.send(
                (
                    "実凸管理画面の生成中に"
                    "エラーが発生しました。"
                ),
                ephemeral=True,
            )
            return

        if not result.teams:
            await interaction.followup.send(
                (
                    "表示できる有効な"
                    "編成がありません。"
                ),
                ephemeral=True,
            )
            return

        view = AttackOverviewView(
            result
        )

        message = await interaction.followup.send(
            embed=view.build_embed(),
            view=view,
            wait=True,
        )

        view.message = message

    # ========================================================
    # /attack target Autocomplete
    #
    # 必ず attack() の「後」に置く。
    # ========================================================

    @attack.autocomplete(
        "target"
    )
    async def attack_target_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[
        app_commands.Choice[str]
    ]:
        """
        /attack target の候補。

        All + 有効Player名を返す。
        """

        _ = interaction

        try:
            targets = await asyncio.to_thread(
                self.overview_service
                .autocomplete_targets,
                current,
                25,
            )

        except Exception as error:
            logger.error(
                (
                    "Attack target autocomplete "
                    "failed: current={!r}, "
                    "error={!r}"
                ),
                current,
                error,
            )

            return []

        return [
            app_commands.Choice(
                name=target,
                value=target,
            )
            for target in targets
        ]


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        AttackCog(bot)
    )