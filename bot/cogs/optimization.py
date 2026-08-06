from __future__ import annotations

import asyncio
from dataclasses import dataclass

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger
from sqlalchemy import select

from bot.core.database import session_scope
from bot.models import Raid
from bot.services import (
    UnionAssignmentPlan,
    UnionAssignmentService,
)
from bot.services.optimization.session_service import (
    OptimizationSessionService,
    OptimizationSessionState,
)


@dataclass
class OptimizationUpdateSession:
    """チャンネルごとの最適化自動更新Session。"""

    channel_id: int
    owner_id: int

    raid_id: int

    message: discord.Message
    view: "OptimizationStopView"

    interval_minutes: int

    task: asyncio.Task[None]


class OptimizationStopView(
    discord.ui.View
):
    """最適化プランの更新終了ボタン。"""

    def __init__(
        self,
        cog: "OptimizationCog",
        channel_id: int,
        owner_id: int,
    ) -> None:
        # Bot再起動後も使用するPersistent View。
        super().__init__(
            timeout=None
        )

        self.cog = cog
        self.channel_id = channel_id
        self.owner_id = owner_id

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """
        /optimizeを開始した本人、
        またはサーバー管理権限を持つ人だけ
        更新を終了できる。
        """

        if (
            interaction.user.id
            == self.owner_id
        ):
            return True

        if (
            isinstance(
                interaction.user,
                discord.Member,
            )
            and interaction.user
            .guild_permissions
            .manage_guild
        ):
            return True

        await interaction.response.send_message(
            (
                "この自動更新を終了できるのは、"
                "開始したユーザーまたは"
                "サーバー管理者です。"
            ),
            ephemeral=True,
        )

        return False

    @discord.ui.button(
        label="更新終了",
        style=discord.ButtonStyle.danger,
        emoji="⏹️",
        custom_id=(
            "nikke_union_optimization_stop"
        ),
    )
    async def stop_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        """最適化自動更新を終了する。"""

        _ = button

        stopped = await self.cog.stop_session(
            self.channel_id
        )

        for item in self.children:
            if isinstance(
                item,
                discord.ui.Button,
            ):
                item.disabled = True

        self.stop()

        current_content = ""

        if interaction.message is not None:
            current_content = (
                interaction.message.content
                or ""
            )

        if stopped:
            status = (
                "\n\n"
                "⏹️ **最適化プランの"
                "自動更新を終了しました。**"
            )
        else:
            status = (
                "\n\n"
                "⏹️ **自動更新はすでに"
                "終了しています。**"
            )

        await interaction.response.edit_message(
            content=(
                current_content
                + status
            ),
            view=self,
        )


class OptimizationCog(
    commands.Cog
):
    """最適化プランDiscord UI。"""

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:
        self.bot = bot

        self.assignment_service = (
            UnionAssignmentService()
        )

        self.session_service = (
            OptimizationSessionService()
        )

        # channel_id
        # →
        # OptimizationUpdateSession
        self._sessions: dict[
            int,
            OptimizationUpdateSession,
        ] = {}

        self._restore_task: (
            asyncio.Task[None]
            | None
        ) = None

    # ========================================================
    # Cog load
    # ========================================================

    async def cog_load(
        self,
    ) -> None:
        """
        Extensionロード後、
        BotがReadyになったら
        DB Sessionを復元する。
        """

        self._restore_task = (
            asyncio.create_task(
                self._restore_sessions_after_ready(),
                name=(
                    "optimization_restore_sessions"
                ),
            )
        )

    # ========================================================
    # /optimize
    # ========================================================

    @app_commands.command(
        name="optimize",
        description=(
            "最適化プランの自動更新を開始します"
        ),
    )
    @app_commands.describe(
        interval_minutes=(
            "更新間隔（分）。"
            "1～60、デフォルト5分"
        )
    )
    async def optimize(
        self,
        interaction: discord.Interaction,
        interval_minutes: app_commands.Range[
            int,
            1,
            60,
        ] = 5,
    ) -> None:
        """
        コマンドを実行したチャンネルで
        最適化プランの自動更新を開始する。
        """

        channel_id = interaction.channel_id

        if channel_id is None:
            await interaction.response.send_message(
                "チャンネルを取得できませんでした。",
                ephemeral=True,
            )
            return

        # 同一チャンネルでは1Sessionだけ。
        if self.is_running(
            channel_id
        ):
            await interaction.response.send_message(
                (
                    "このチャンネルではすでに"
                    "最適化プランを自動更新しています。\n"
                    "現在のプランの"
                    "「更新終了」を押してから"
                    "再実行してください。"
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(
            thinking=True,
            ephemeral=True,
        )

        # --------------------------------
        # Active Raid確認
        # --------------------------------

        active_raid = await asyncio.to_thread(
            self._get_active_raid
        )

        if active_raid is None:
            await interaction.edit_original_response(
                content=(
                    "Active Raidがありません。"
                )
            )
            return

        raid_id, raid_name = active_raid

        # --------------------------------
        # 初回プラン生成
        # --------------------------------

        try:
            content, embeds = (
                await self._build_update_message(
                    raid_id=raid_id,
                    interval_minutes=(
                        int(interval_minutes)
                    ),
                )
            )

        except Exception:
            logger.exception(
                (
                    "Failed to build initial "
                    "optimization plan"
                )
            )

            await interaction.edit_original_response(
                content=(
                    "最適化プランの生成中に"
                    "エラーが発生しました。"
                )
            )
            return

        channel = interaction.channel

        if channel is None:
            await interaction.edit_original_response(
                content=(
                    "チャンネルを取得できませんでした。"
                )
            )
            return

        view = OptimizationStopView(
            cog=self,
            channel_id=channel_id,
            owner_id=interaction.user.id,
        )

        # --------------------------------
        # 通常のBot Messageとして投稿
        # --------------------------------

        try:
            message = await channel.send(
                content=content,
                embeds=embeds,
                view=view,
            )

        except discord.Forbidden:
            await interaction.edit_original_response(
                content=(
                    "このチャンネルへ"
                    "メッセージを送信する権限がありません。"
                )
            )
            return

        except discord.HTTPException:
            logger.exception(
                (
                    "Failed to send optimization "
                    "message: channel_id={}"
                ),
                channel_id,
            )

            await interaction.edit_original_response(
                content=(
                    "最適化プランの投稿中に"
                    "エラーが発生しました。"
                )
            )
            return

        # --------------------------------
        # SessionをDBへ保存
        # --------------------------------

        try:
            await asyncio.to_thread(
                self.session_service.start,
                channel_id,
                message.id,
                raid_id,
                int(interval_minutes),
                interaction.user.id,
            )

        except Exception:
            logger.exception(
                (
                    "Failed to persist optimization "
                    "session: channel_id={}"
                ),
                channel_id,
            )

            try:
                await message.edit(
                    content=(
                        "⚠️ 最適化Sessionの保存に"
                        "失敗したため、自動更新を"
                        "開始できませんでした。"
                    ),
                    embeds=[],
                    view=None,
                )
            except discord.HTTPException:
                pass

            await interaction.edit_original_response(
                content=(
                    "Sessionの保存中に"
                    "エラーが発生しました。"
                )
            )
            return

        # --------------------------------
        # 自動更新Task開始
        # --------------------------------

        task = asyncio.create_task(
            self._update_loop(
                channel_id=channel_id,
                raid_id=raid_id,
                message=message,
                view=view,
                interval_minutes=(
                    int(interval_minutes)
                ),
            ),
            name=(
                "optimization_update_"
                f"{channel_id}"
            ),
        )

        self._sessions[
            channel_id
        ] = OptimizationUpdateSession(
            channel_id=channel_id,
            owner_id=interaction.user.id,
            raid_id=raid_id,
            message=message,
            view=view,
            interval_minutes=(
                int(interval_minutes)
            ),
            task=task,
        )

        await interaction.edit_original_response(
            content=(
                "✅ 最適化プランの"
                "自動更新を開始しました。\n"
                f"Raid: **{raid_name}**\n"
                f"更新間隔: "
                f"**{interval_minutes}分**"
            )
        )

        logger.info(
            (
                "Optimization auto update started: "
                "channel_id={}, "
                "raid_id={}, "
                "owner_id={}, "
                "interval_minutes={}"
            ),
            channel_id,
            raid_id,
            interaction.user.id,
            interval_minutes,
        )

    # ========================================================
    # Session state
    # ========================================================

    def is_running(
        self,
        channel_id: int,
    ) -> bool:
        """指定チャンネルで更新中か確認する。"""

        session = self._sessions.get(
            channel_id
        )

        if session is None:
            return False

        return not session.task.done()

    async def stop_session(
        self,
        channel_id: int,
    ) -> bool:
        """
        指定チャンネルの自動更新を終了する。

        メモリTaskだけでなく、
        DBのactiveもFalseにする。
        """

        memory_session = self._sessions.pop(
            channel_id,
            None,
        )

        try:
            persistent_state = await asyncio.to_thread(
                self.session_service.get_by_channel,
                channel_id,
            )
        except Exception:
            logger.exception(
                (
                    "Failed to read persistent "
                    "optimization session: "
                    "channel_id={}"
                ),
                channel_id,
            )

            persistent_state = None

        was_active = (
            persistent_state is not None
            and persistent_state.active
        )

        if memory_session is not None:
            if not memory_session.task.done():
                memory_session.task.cancel()

        if was_active:
            try:
                await asyncio.to_thread(
                    self.session_service.stop,
                    channel_id,
                )

            except Exception:
                logger.exception(
                    (
                        "Failed to stop persistent "
                        "optimization session: "
                        "channel_id={}"
                    ),
                    channel_id,
                )

        stopped = (
            memory_session is not None
            or was_active
        )

        if stopped:
            logger.info(
                (
                    "Optimization auto update stopped: "
                    "channel_id={}"
                ),
                channel_id,
            )

        return stopped

    # ========================================================
    # Update loop
    # ========================================================

    async def _update_loop(
        self,
        channel_id: int,
        raid_id: int,
        message: discord.Message,
        view: OptimizationStopView,
        interval_minutes: int,
    ) -> None:
        """
        更新終了ボタンが押されるまで
        最適化プランを再計算し続ける。
        """

        interval_seconds = (
            interval_minutes
            * 60
        )

        try:
            while True:
                await asyncio.sleep(
                    interval_seconds
                )

                try:
                    content, embeds = (
                        await self._build_update_message(
                            raid_id=raid_id,
                            interval_minutes=(
                                interval_minutes
                            ),
                        )
                    )

                    await message.edit(
                        content=content,
                        embeds=embeds,
                        view=view,
                    )

                    logger.info(
                        (
                            "Optimization plan updated: "
                            "channel_id={}, raid_id={}"
                        ),
                        channel_id,
                        raid_id,
                    )

                except discord.NotFound:
                    logger.warning(
                        (
                            "Optimization message "
                            "was deleted: "
                            "channel_id={}"
                        ),
                        channel_id,
                    )

                    await (
                        self._deactivate_persistent_session(
                            channel_id
                        )
                    )

                    return

                except discord.Forbidden:
                    logger.warning(
                        (
                            "Cannot edit optimization "
                            "message: channel_id={}"
                        ),
                        channel_id,
                    )

                    await (
                        self._deactivate_persistent_session(
                            channel_id
                        )
                    )

                    return

                except Exception:
                    # 1回の計算失敗だけでは
                    # 自動更新自体を終了しない。
                    logger.exception(
                        (
                            "Optimization update failed: "
                            "channel_id={}"
                        ),
                        channel_id,
                    )

        except asyncio.CancelledError:
            raise

        finally:
            current = self._sessions.get(
                channel_id
            )

            current_task = (
                asyncio.current_task()
            )

            if (
                current is not None
                and current.task
                is current_task
            ):
                self._sessions.pop(
                    channel_id,
                    None,
                )

    # ========================================================
    # Restore
    # ========================================================

    async def _restore_sessions_after_ready(
        self,
    ) -> None:
        """Bot再起動後にactive Sessionを復元する。"""

        await self.bot.wait_until_ready()

        try:
            states = await asyncio.to_thread(
                self.session_service.list_active
            )

        except Exception:
            logger.exception(
                (
                    "Failed to load persistent "
                    "optimization sessions"
                )
            )
            return

        if not states:
            logger.info(
                "No optimization sessions to restore"
            )
            return

        logger.info(
            (
                "Restoring {} optimization "
                "session(s)"
            ),
            len(states),
        )

        for state in states:
            if (
                state.channel_id
                in self._sessions
            ):
                continue

            await self._restore_one_session(
                state
            )

    async def _restore_one_session(
        self,
        state: OptimizationSessionState,
    ) -> None:
        """保存されたSessionを1件復元する。"""

        if state.message_id is None:
            logger.warning(
                (
                    "Persistent optimization session "
                    "has no message_id: channel_id={}"
                ),
                state.channel_id,
            )

            await self._deactivate_persistent_session(
                state.channel_id
            )
            return

        # --------------------------------
        # Channel取得
        # --------------------------------

        channel = self.bot.get_channel(
            state.channel_id
        )

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(
                    state.channel_id
                )

            except discord.NotFound:
                await (
                    self._deactivate_persistent_session(
                        state.channel_id
                    )
                )
                return

            except discord.Forbidden:
                await (
                    self._deactivate_persistent_session(
                        state.channel_id
                    )
                )
                return

            except discord.HTTPException:
                logger.exception(
                    (
                        "Failed to fetch optimization "
                        "channel: channel_id={}"
                    ),
                    state.channel_id,
                )
                return

        if not hasattr(
            channel,
            "fetch_message",
        ):
            logger.warning(
                (
                    "Optimization channel cannot "
                    "fetch messages: channel_id={}"
                ),
                state.channel_id,
            )

            await self._deactivate_persistent_session(
                state.channel_id
            )
            return

        # --------------------------------
        # Message取得
        # --------------------------------

        try:
            message = await channel.fetch_message(
                state.message_id
            )

        except discord.NotFound:
            logger.warning(
                (
                    "Persistent optimization message "
                    "not found: channel_id={}, "
                    "message_id={}"
                ),
                state.channel_id,
                state.message_id,
            )

            await self._deactivate_persistent_session(
                state.channel_id
            )
            return

        except discord.Forbidden:
            logger.warning(
                (
                    "Cannot fetch persistent "
                    "optimization message: "
                    "channel_id={}"
                ),
                state.channel_id,
            )

            await self._deactivate_persistent_session(
                state.channel_id
            )
            return

        except discord.HTTPException:
            logger.exception(
                (
                    "Failed to fetch persistent "
                    "optimization message: "
                    "channel_id={}, message_id={}"
                ),
                state.channel_id,
                state.message_id,
            )
            return

        # --------------------------------
        # Persistent View登録
        # --------------------------------

        view = OptimizationStopView(
            cog=self,
            channel_id=state.channel_id,
            owner_id=(
                state.started_by_discord_id
            ),
        )

        self.bot.add_view(
            view,
            message_id=state.message_id,
        )

        # --------------------------------
        # 再起動直後に一度更新
        # --------------------------------

        try:
            content, embeds = (
                await self._build_update_message(
                    raid_id=state.raid_id,
                    interval_minutes=(
                        state.interval_minutes
                    ),
                )
            )

            await message.edit(
                content=content,
                embeds=embeds,
                view=view,
            )

        except discord.NotFound:
            await self._deactivate_persistent_session(
                state.channel_id
            )
            return

        except discord.Forbidden:
            await self._deactivate_persistent_session(
                state.channel_id
            )
            return

        except Exception:
            # 計算失敗していても、
            # 次回更新で復旧する可能性があるので
            # Session自体は復元する。
            logger.exception(
                (
                    "Initial restored optimization "
                    "update failed: channel_id={}"
                ),
                state.channel_id,
            )

        # --------------------------------
        # 更新Task再作成
        # --------------------------------

        task = asyncio.create_task(
            self._update_loop(
                channel_id=state.channel_id,
                raid_id=state.raid_id,
                message=message,
                view=view,
                interval_minutes=(
                    state.interval_minutes
                ),
            ),
            name=(
                "optimization_update_"
                f"{state.channel_id}"
            ),
        )

        self._sessions[
            state.channel_id
        ] = OptimizationUpdateSession(
            channel_id=state.channel_id,
            owner_id=(
                state.started_by_discord_id
            ),
            raid_id=state.raid_id,
            message=message,
            view=view,
            interval_minutes=(
                state.interval_minutes
            ),
            task=task,
        )

        logger.info(
            (
                "Optimization session restored: "
                "channel_id={}, "
                "message_id={}, "
                "raid_id={}, "
                "interval_minutes={}"
            ),
            state.channel_id,
            state.message_id,
            state.raid_id,
            state.interval_minutes,
        )

    async def _deactivate_persistent_session(
        self,
        channel_id: int,
    ) -> None:
        """DB Sessionをactive=Falseにする。"""

        try:
            await asyncio.to_thread(
                self.session_service.stop,
                channel_id,
            )

        except Exception:
            logger.exception(
                (
                    "Failed to deactivate "
                    "optimization session: "
                    "channel_id={}"
                ),
                channel_id,
            )

    # ========================================================
    # Plan generation
    # ========================================================

    async def _build_update_message(
        self,
        raid_id: int,
        interval_minutes: int,
    ) -> tuple[
        str,
        list[discord.Embed],
    ]:
        """指定Raidの最新最適化プランを生成する。"""

        raid = await asyncio.to_thread(
            self._get_raid_by_id,
            raid_id,
        )

        now = discord.utils.utcnow()

        timestamp = int(
            now.timestamp()
        )

        if raid is None:
            content = (
                "## 最適化プラン\n\n"
                "⚠️ 対象Raidが見つかりません。\n\n"
                f"Raid ID: **{raid_id}**\n"
                f"更新間隔: **{interval_minutes}分**\n"
                f"最終確認: <t:{timestamp}:R>"
            )

            return (
                content,
                [],
            )

        _, raid_name = raid

        plan = await asyncio.to_thread(
            self.assignment_service.build_for_raid,
            raid_id,
            3,
        )

        content = self._build_header(
            raid_name=raid_name,
            plan=plan,
            interval_minutes=(
                interval_minutes
            ),
            timestamp=timestamp,
        )

        embeds = self._build_embeds(
            plan
        )

        return (
            content,
            embeds,
        )

    def _get_active_raid(
        self,
    ) -> tuple[int, str] | None:
        """現在のActive Raidを取得する。"""

        with session_scope() as session:
            raid = session.scalar(
                select(Raid)
                .where(
                    Raid.active.is_(True)
                )
                .order_by(
                    Raid.id.desc()
                )
            )

            if raid is None:
                return None

            return (
                raid.id,
                raid.name,
            )

    def _get_raid_by_id(
        self,
        raid_id: int,
    ) -> tuple[int, str] | None:
        """IDからRaidを取得する。"""

        with session_scope() as session:
            raid = session.scalar(
                select(Raid)
                .where(
                    Raid.id == raid_id
                )
            )

            if raid is None:
                return None

            return (
                raid.id,
                raid.name,
            )

    # ========================================================
    # Discord rendering
    # ========================================================

    def _build_header(
        self,
        raid_name: str,
        plan: UnionAssignmentPlan,
        interval_minutes: int,
        timestamp: int,
    ) -> str:
        """最適化メッセージ上部を生成する。"""

        return (
            "## 最適化プラン\n"
            f"Raid: **{raid_name}**\n"
            f"割り当て数: **{plan.attack_count}凸**\n"
            "合計Damage: "
            f"**{plan.total_nominal_damage:,}**\n"
            "有効Damage: "
            f"**{plan.total_effective_damage:,}**\n\n"
            f"更新間隔: **{interval_minutes}分**\n"
            f"最終更新: <t:{timestamp}:R>\n\n"
            "※ 攻撃順序は考慮していません。\n"
            "※ DamageRecordが更新されると、"
            "次回更新時に再最適化されます。"
        )

    def _build_embeds(
        self,
        plan: UnionAssignmentPlan,
    ) -> list[discord.Embed]:
        """Bossごとの攻撃割り当てEmbedを作る。"""

        if not plan.boss_summaries:
            embed = discord.Embed(
                title="割り当てなし",
                description=(
                    "現在、最適化に使用できる"
                    "DamageRecordがありません。"
                ),
            )

            return [
                embed
            ]

        embeds: list[
            discord.Embed
        ] = []

        for boss in plan.boss_summaries:
            lines: list[str] = []

            for assignment in boss.assignments:
                lines.append(
                    (
                        f"**{assignment.player_name}**"
                        f" / Team #{assignment.team_no}"
                        f" / **{assignment.damage:,}**"
                    )
                )

                if assignment.character_names:
                    characters = " / ".join(
                        assignment.character_names
                    )

                    lines.append(
                        f"`{characters}`"
                    )

                lines.append("")

            chunks = self._split_lines(
                lines=lines,
                max_length=3800,
            )

            for chunk_index, chunk in enumerate(
                chunks,
                start=1,
            ):
                if len(chunks) == 1:
                    title = (
                        f"{boss.boss_name} "
                        f"| Phase {boss.phase_no}"
                    )
                else:
                    title = (
                        f"{boss.boss_name} "
                        f"| Phase {boss.phase_no} "
                        f"({chunk_index}/{len(chunks)})"
                    )

                embed = discord.Embed(
                    title=title,
                    description=chunk,
                )

                embed.add_field(
                    name="Boss HP",
                    value=f"{boss.max_hp:,}",
                    inline=True,
                )

                embed.add_field(
                    name="割り当てDamage",
                    value=(
                        f"{boss.assigned_damage:,}"
                    ),
                    inline=True,
                )

                embed.add_field(
                    name="Overkill",
                    value=(
                        f"{boss.overkill_damage:,}"
                    ),
                    inline=True,
                )

                embeds.append(
                    embed
                )

        # Discordは1メッセージ最大10 Embed。
        return embeds[:10]

    def _split_lines(
        self,
        lines: list[str],
        max_length: int,
    ) -> list[str]:
        """Discord Embed制限に合わせて分割する。"""

        chunks: list[str] = []

        current_lines: list[str] = []
        current_length = 0

        for line in lines:
            added_length = (
                len(line) + 1
            )

            if (
                current_lines
                and current_length
                + added_length
                > max_length
            ):
                chunks.append(
                    "\n".join(
                        current_lines
                    )
                )

                current_lines = []
                current_length = 0

            current_lines.append(
                line
            )

            current_length += (
                added_length
            )

        if current_lines:
            chunks.append(
                "\n".join(
                    current_lines
                )
            )

        if not chunks:
            chunks.append(
                "割り当てなし"
            )

        return chunks

    # ========================================================
    # Cog unload
    # ========================================================

    def cog_unload(
        self,
    ) -> None:
        """
        Bot終了時にTaskだけcancelする。

        DBのactiveはFalseにしない。
        次回起動時に復元するため。
        """

        if (
            self._restore_task is not None
            and not self._restore_task.done()
        ):
            self._restore_task.cancel()

        for session in list(
            self._sessions.values()
        ):
            if not session.task.done():
                session.task.cancel()

        self._sessions.clear()


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        OptimizationCog(bot)
    )