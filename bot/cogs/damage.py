import discord
from discord import app_commands
from discord.ext import commands

from bot.core.logger import get_logger
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
from bot.services import DamageService


logger = get_logger()


class DamageCog(commands.Cog):
    """ダメージ管理用Discordコマンド。"""

    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:
        self.bot = bot
        self.damage_service = DamageService()

    @app_commands.command(
        name="damage-add",
        description="ダメージを手動登録します。",
    )
    @app_commands.describe(
        team_no="使用した編成番号",
        boss_no="攻撃したBoss番号（1～5）",
        damage="与えたダメージ",
    )
    async def damage_add(
        self,
        interaction: discord.Interaction,
        team_no: int,
        boss_no: int,
        damage: int,
    ) -> None:
        discord_id = str(
            interaction.user.id
        )

        try:
            record, boss, previous_hp = (
                self.damage_service.register_damage(
                    discord_id=discord_id,
                    team_no=team_no,
                    boss_no=boss_no,
                    damage=damage,
                )
            )

        except PlayerNotFoundError:
            await interaction.response.send_message(
                (
                    "編成が登録されていません。\n"
                    "先に `/team-add` で編成を登録してください。"
                ),
                ephemeral=True,
            )
            return

        except PlayerInactiveError:
            await interaction.response.send_message(
                "このプレイヤーは現在無効化されています。",
                ephemeral=True,
            )
            return

        except InvalidTeamNumberError:
            await interaction.response.send_message(
                "編成番号は1以上で指定してください。",
                ephemeral=True,
            )
            return

        except TeamNotFoundError:
            await interaction.response.send_message(
                (
                    f"編成 #{team_no} が見つかりません。\n"
                    "`/team-list` で確認してください。"
                ),
                ephemeral=True,
            )
            return

        except TeamInactiveError:
            await interaction.response.send_message(
                f"編成 #{team_no} は現在無効です。",
                ephemeral=True,
            )
            return

        except InvalidBossNumberError:
            await interaction.response.send_message(
                "Boss番号は1～5で指定してください。",
                ephemeral=True,
            )
            return

        except ActiveRaidNotFoundError:
            await interaction.response.send_message(
                "現在開催中のレイドがありません。",
                ephemeral=True,
            )
            return

        except BossNotFoundError:
            await interaction.response.send_message(
                (
                    f"Boss {boss_no} が登録されていません。\n"
                    "先に `/boss-set` を実行してください。"
                ),
                ephemeral=True,
            )
            return

        except InvalidDamageError:
            await interaction.response.send_message(
                "ダメージは1以上で指定してください。",
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                (
                    "Damage registration failed: "
                    "discord_id={}, team_no={}, "
                    "boss_no={}, damage={}"
                ),
                discord_id,
                team_no,
                boss_no,
                damage,
            )

            await interaction.response.send_message(
                "ダメージ登録中にエラーが発生しました。",
                ephemeral=True,
            )
            return

        logger.info(
            (
                "Damage registered: "
                "record_id={}, team_no={}, "
                "boss_no={}, damage={}"
            ),
            record.id,
            team_no,
            boss_no,
            record.damage,
        )

        await interaction.response.send_message(
            (
                "**ダメージを登録しました。**\n\n"
                f"編成: **#{team_no}**\n"
                f"Boss: **{boss.boss_no} - {boss.name}**\n"
                f"Damage: **{record.damage:,}**\n\n"
                "**Boss HP**\n"
                f"`{previous_hp:,}`\n"
                "↓\n"
                f"`{boss.current_hp:,}`"
            ),
            ephemeral=True,
        )


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        DamageCog(bot)
    )