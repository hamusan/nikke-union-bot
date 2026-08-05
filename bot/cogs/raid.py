import discord
from discord import app_commands
from discord.ext import commands

from bot.core.logger import get_logger
from bot.exceptions import (
    ActiveRaidNotFoundError,
    BossNotFoundError,
    InvalidBossHpError,
    InvalidBossNameError,
    InvalidBossNumberError,
    InvalidRaidNameError,
    RaidAlreadyExistsError,
)
from bot.services import RaidService


logger = get_logger()


class RaidCog(commands.Cog):
    """ユニオンレイド・Boss管理用Discordコマンド。"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.raid_service = RaidService()

    @app_commands.command(
        name="raid-create",
        description="新しいユニオンレイドを開始します。",
    )
    @app_commands.describe(
        name="レイド名（例: 2026年8月ユニオンレイド）",
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def raid_create(
        self,
        interaction: discord.Interaction,
        name: str,
    ) -> None:
        try:
            raid = self.raid_service.create_raid(
                name=name
            )

        except InvalidRaidNameError:
            await interaction.response.send_message(
                "レイド名を入力してください。",
                ephemeral=True,
            )
            return

        except RaidAlreadyExistsError:
            await interaction.response.send_message(
                "同じ名前のレイドがすでに存在します。",
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                "Raid creation failed: name={}",
                name,
            )

            await interaction.response.send_message(
                "レイドの作成中にエラーが発生しました。",
                ephemeral=True,
            )
            return

        logger.info(
            "Raid created: id={}, name={}",
            raid.id,
            raid.name,
        )

        await interaction.response.send_message(
            (
                "新しいユニオンレイドを開始しました。\n\n"
                f"**{raid.name}**\n\n"
                "以前のレイドは自動的に終了扱いになります。"
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="raid-current",
        description="現在開催中のユニオンレイドを表示します。",
    )
    async def raid_current(
        self,
        interaction: discord.Interaction,
    ) -> None:
        try:
            raid = self.raid_service.get_active_raid()

        except ActiveRaidNotFoundError:
            await interaction.response.send_message(
                "現在開催中のレイドはありません。",
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                "Failed to get active raid."
            )

            await interaction.response.send_message(
                "レイド情報の取得中にエラーが発生しました。",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            (
                "**現在開催中のユニオンレイド**\n\n"
                f"{raid.name}"
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="boss-set",
        description="現在のレイドにBossを登録・更新します。",
    )
    @app_commands.describe(
        boss_no="Boss番号（1～5）",
        name="Boss名",
        max_hp="Bossの最大HP",
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def boss_set(
        self,
        interaction: discord.Interaction,
        boss_no: int,
        name: str,
        max_hp: int,
    ) -> None:
        try:
            boss = self.raid_service.set_boss(
                boss_no=boss_no,
                name=name,
                max_hp=max_hp,
            )

        except ActiveRaidNotFoundError:
            await interaction.response.send_message(
                (
                    "現在開催中のレイドがありません。\n"
                    "先に `/raid-create` を実行してください。"
                ),
                ephemeral=True,
            )
            return

        except InvalidBossNumberError:
            await interaction.response.send_message(
                "Boss番号は1～5で指定してください。",
                ephemeral=True,
            )
            return

        except InvalidBossNameError:
            await interaction.response.send_message(
                "Boss名を入力してください。",
                ephemeral=True,
            )
            return

        except InvalidBossHpError:
            await interaction.response.send_message(
                "最大HPは1以上の整数で指定してください。",
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                "Boss set failed: boss_no={}",
                boss_no,
            )

            await interaction.response.send_message(
                "Boss設定中にエラーが発生しました。",
                ephemeral=True,
            )
            return

        logger.info(
            "Boss configured: id={}, boss_no={}, name={}, max_hp={}",
            boss.id,
            boss.boss_no,
            boss.name,
            boss.max_hp,
        )

        await interaction.response.send_message(
            (
                f"**Boss {boss.boss_no}** を設定しました。\n\n"
                f"名前: **{boss.name}**\n"
                f"最大HP: **{boss.max_hp:,}**"
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="boss-hp",
        description="Bossの現在HPを変更します。",
    )
    @app_commands.describe(
        boss_no="Boss番号（1～5）",
        current_hp="現在の残HP",
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def boss_hp(
        self,
        interaction: discord.Interaction,
        boss_no: int,
        current_hp: int,
    ) -> None:
        try:
            boss = self.raid_service.set_current_hp(
                boss_no=boss_no,
                current_hp=current_hp,
            )

        except ActiveRaidNotFoundError:
            await interaction.response.send_message(
                "現在開催中のレイドがありません。",
                ephemeral=True,
            )
            return

        except InvalidBossNumberError:
            await interaction.response.send_message(
                "Boss番号は1～5で指定してください。",
                ephemeral=True,
            )
            return

        except BossNotFoundError:
            await interaction.response.send_message(
                (
                    "そのBossはまだ登録されていません。\n"
                    "先に `/boss-set` を実行してください。"
                ),
                ephemeral=True,
            )
            return

        except InvalidBossHpError:
            await interaction.response.send_message(
                (
                    "HPの値が不正です。\n"
                    "0以上かつ最大HP以下で指定してください。"
                ),
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                "Boss HP update failed: boss_no={}",
                boss_no,
            )

            await interaction.response.send_message(
                "Boss HPの更新中にエラーが発生しました。",
                ephemeral=True,
            )
            return

        logger.info(
            "Boss HP updated: boss_no={}, current_hp={}",
            boss.boss_no,
            boss.current_hp,
        )

        await interaction.response.send_message(
            (
                f"**Boss {boss.boss_no} - {boss.name}**\n\n"
                f"現在HPを **{boss.current_hp:,}** に変更しました。"
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="boss-list",
        description="現在のレイドのBoss一覧を表示します。",
    )
    async def boss_list(
        self,
        interaction: discord.Interaction,
    ) -> None:
        try:
            raid = self.raid_service.get_active_raid()
            bosses = self.raid_service.list_bosses()

        except ActiveRaidNotFoundError:
            await interaction.response.send_message(
                "現在開催中のレイドはありません。",
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                "Failed to get boss list."
            )

            await interaction.response.send_message(
                "Boss一覧の取得中にエラーが発生しました。",
                ephemeral=True,
            )
            return

        if not bosses:
            await interaction.response.send_message(
                (
                    f"**{raid.name}**\n\n"
                    "Bossはまだ登録されていません。"
                ),
                ephemeral=True,
            )
            return

        boss_sections: list[str] = []

        for boss in bosses:
            hp_percent = (
                boss.current_hp / boss.max_hp * 100
                if boss.max_hp > 0
                else 0
            )

            boss_sections.append(
                (
                    f"**Boss {boss.boss_no}: {boss.name}**\n"
                    f"HP: `{boss.current_hp:,}`"
                    f" / `{boss.max_hp:,}`\n"
                    f"残り: **{hp_percent:.1f}%**"
                )
            )

        message = (
            f"## {raid.name}\n\n"
            + "\n\n".join(boss_sections)
        )

        await interaction.response.send_message(
            message,
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RaidCog(bot))