import discord
from discord import app_commands
from discord.ext import commands

from bot.core.logger import get_logger
from bot.exceptions import PlayerAlreadyExistsError
from bot.services import PlayerService


logger = get_logger()


class PlayerCog(commands.Cog):
    """Player管理用のDiscordコマンド。"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.player_service = PlayerService()

    @app_commands.command(
        name="player-register",
        description="自分をユニオンレイドメンバーとして登録します。",
    )
    @app_commands.describe(
        nickname="NIKKEで使用しているプレイヤー名",
    )
    async def player_register(
        self,
        interaction: discord.Interaction,
        nickname: str | None = None,
    ) -> None:
        discord_id = str(interaction.user.id)

        player_name = (
            nickname.strip()
            if nickname is not None and nickname.strip()
            else interaction.user.display_name
        )

        try:
            player = self.player_service.register_player(
                discord_id=discord_id,
                nickname=player_name,
            )

        except PlayerAlreadyExistsError:
            await interaction.response.send_message(
                "すでにプレイヤー登録されています。",
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                "Player registration failed: discord_id={}",
                discord_id,
            )

            await interaction.response.send_message(
                "プレイヤー登録中にエラーが発生しました。",
                ephemeral=True,
            )
            return

        logger.info(
            "Player registered: id={}, discord_id={}, nickname={}",
            player.id,
            player.discord_id,
            player.nickname,
        )

        await interaction.response.send_message(
            (
                "プレイヤー登録が完了しました。\n\n"
                f"**プレイヤー名:** {player.nickname}"
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PlayerCog(bot))