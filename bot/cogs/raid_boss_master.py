import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from bot.services import BossMasterService


class RaidBossMasterCog(commands.Cog):
    """
    Raid Boss Master設定用Discord Cog。

    Boss名やPhase HPを自由入力せず、
    固定Boss Masterから選択して設定する。
    """

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:
        self.bot = bot
        self.service = BossMasterService()

    # ========================================================
    # /raid-boss-set
    # ========================================================

    @app_commands.command(
        name="raid-boss-set",
        description=(
            "RaidのBoss #1～#5を"
            "固定Boss一覧から設定します"
        ),
    )
    @app_commands.describe(
        boss_no="Boss番号 1～5",
        boss="設定するBoss",
    )
    async def raid_boss_set(
        self,
        interaction: discord.Interaction,
        boss_no: app_commands.Range[int, 1, 5],
        boss: str,
    ) -> None:
        """
        Active RaidのBoss枠へ
        Boss Masterを設定する。
        """

        try:
            result = (
                self.service.set_active_raid_boss(
                    boss_no=int(boss_no),
                    boss_key=boss,
                )
            )

            slots = (
                self.service.list_active_raid_bosses()
            )

            slot = next(
                (
                    item
                    for item in slots
                    if item.boss_no
                    == result.boss_no
                ),
                None,
            )

        except ValueError as exc:
            await interaction.response.send_message(
                f"⚠️ {exc}",
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                (
                    "Failed to set Raid Boss: "
                    "boss_no={}, boss_key={}"
                ),
                boss_no,
                boss,
            )

            await interaction.response.send_message(
                "Boss設定中にエラーが発生しました。",
                ephemeral=True,
            )
            return

        lines = [
            "✅ **Raid Bossを設定しました**",
            "",
            f"Boss #{result.boss_no}",
            f"Boss: **{result.boss_name}**",
            f"Key: `{result.boss_key}`",
        ]

        if (
            slot is not None
            and slot.phase_hps
        ):
            lines.append("")
            lines.append("**Phase HP**")

            for (
                phase_no,
                max_hp,
            ) in slot.phase_hps:
                lines.append(
                    (
                        f"- Phase {phase_no}: "
                        f"{max_hp:,}"
                    )
                )

        await interaction.response.send_message(
            "\n".join(lines)
        )

    # ========================================================
    # Boss autocomplete
    # ========================================================

    @raid_boss_set.autocomplete(
        "boss"
    )
    async def boss_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[
        app_commands.Choice[str]
    ]:
        """
        boss_master.pyの固定Boss一覧から
        オートコンプリート候補を返す。
        """

        # 現在はinteraction自体は使用しない。
        _ = interaction

        normalized = (
            current.strip().casefold()
        )

        choices: list[
            app_commands.Choice[str]
        ] = []

        for boss in (
            self.service.list_master_bosses()
        ):
            if normalized:
                name_match = (
                    normalized
                    in boss.name.casefold()
                )

                key_match = (
                    normalized
                    in boss.key.casefold()
                )

                if (
                    not name_match
                    and not key_match
                ):
                    continue

            choices.append(
                app_commands.Choice(
                    name=boss.name,
                    value=boss.key,
                )
            )

            # Discord autocompleteは最大25件。
            if len(choices) >= 25:
                break

        return choices

    # ========================================================
    # /raid-boss-list
    # ========================================================

    @app_commands.command(
        name="raid-boss-list",
        description=(
            "現在のRaid Boss #1～#5を表示します"
        ),
    )
    async def raid_boss_list(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """
        Active RaidのBoss設定を表示する。
        """

        try:
            slots = (
                self.service.list_active_raid_bosses()
            )

        except ValueError as exc:
            await interaction.response.send_message(
                f"⚠️ {exc}",
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                "Failed to list Raid Bosses"
            )

            await interaction.response.send_message(
                "Boss一覧取得中にエラーが発生しました。",
                ephemeral=True,
            )
            return

        lines = [
            "## Raid Boss",
            "",
        ]

        for slot in slots:
            lines.append(
                f"### Boss #{slot.boss_no}"
            )

            # --------------------------------------------
            # Boss row自体が存在しない
            # --------------------------------------------

            if slot.boss_id is None:
                lines.append(
                    "未設定"
                )
                lines.append("")
                continue

            # --------------------------------------------
            # 念のためBoss名が無い場合
            # --------------------------------------------

            if slot.boss_name is None:
                lines.append(
                    "⚠️ Boss名なし"
                )
                lines.append("")
                continue

            lines.append(
                f"**{slot.boss_name}**"
            )

            # --------------------------------------------
            # Boss Master登録済み
            # --------------------------------------------

            if (
                slot.master_registered
                and slot.boss_key is not None
            ):
                lines.append(
                    f"Key: `{slot.boss_key}`"
                )

                if slot.phase_hps:
                    for (
                        phase_no,
                        max_hp,
                    ) in slot.phase_hps:
                        lines.append(
                            (
                                f"- Phase {phase_no}: "
                                f"{max_hp:,}"
                            )
                        )

                else:
                    lines.append(
                        "⚠️ Phase情報なし"
                    )

            # --------------------------------------------
            # 旧DB Boss
            # --------------------------------------------

            else:
                lines.append(
                    "⚠️ Boss Master未登録"
                )

            lines.append("")

        await interaction.response.send_message(
            "\n".join(lines)
        )


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        RaidBossMasterCog(bot)
    )