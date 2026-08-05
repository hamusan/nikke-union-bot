import discord
from discord import app_commands
from discord.ext import commands

from bot.core.logger import get_logger
from bot.exceptions import (
    PlayerAlreadyExistsError,
    PlayerAlreadyInactiveError,
    PlayerNotFoundError,
)
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
            player, reactivated = self.player_service.register_player(
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

        if reactivated:
            logger.info(
                "Player reactivated: id={}, discord_id={}, nickname={}",
                player.id,
                player.discord_id,
                player.nickname,
            )

            message = (
                "プレイヤーを再有効化しました。\n\n"
                f"**プレイヤー名:** {player.nickname}"
            )

        else:
            logger.info(
                "Player registered: id={}, discord_id={}, nickname={}",
                player.id,
                player.discord_id,
                player.nickname,
            )

            message = (
                "プレイヤー登録が完了しました。\n\n"
                f"**プレイヤー名:** {player.nickname}"
            )

        await interaction.response.send_message(
            message,
            ephemeral=True,
        )
    
    @app_commands.command(
        name="player-list",
        description="登録されているプレイヤー一覧を表示します。",
    )
    async def player_list(
        self,
        interaction: discord.Interaction,
    ) -> None:
        try:
            players = self.player_service.list_active_players()

        except Exception:
            logger.exception(
                "Failed to get player list."
            )

            await interaction.response.send_message(
                "プレイヤー一覧の取得中にエラーが発生しました。",
                ephemeral=True,
            )
            return

        if not players:
            await interaction.response.send_message(
                "現在登録されているプレイヤーはいません。",
                ephemeral=True,
            )
            return

        player_lines = [
            f"{index}. {player.nickname}"
            for index, player in enumerate(
                players,
                start=1,
            )
        ]

        message = (
            "**登録プレイヤー一覧**\n\n"
            + "\n".join(player_lines)
            + f"\n\n合計: **{len(players)}人**"
        )

        await interaction.response.send_message(
            message,
            ephemeral=True,
        )

    @app_commands.command(
        name="player-deactivate",
        description="プレイヤーを無効化します。",
    )
    @app_commands.describe(
        member="無効化するDiscordメンバー",
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def player_deactivate(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        discord_id = str(member.id)

        try:
            player = self.player_service.deactivate_player(
                discord_id
            )

        except PlayerNotFoundError:
            await interaction.response.send_message(
                "そのメンバーはプレイヤー登録されていません。",
                ephemeral=True,
            )
            return

        except PlayerAlreadyInactiveError:
            await interaction.response.send_message(
                "そのプレイヤーはすでに無効化されています。",
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                "Player deactivation failed: discord_id={}",
                discord_id,
            )

            await interaction.response.send_message(
                "プレイヤーの無効化中にエラーが発生しました。",
                ephemeral=True,
            )
            return

        logger.info(
            "Player deactivated: id={}, discord_id={}, nickname={}",
            player.id,
            player.discord_id,
            player.nickname,
        )

        await interaction.response.send_message(
            (
                "プレイヤーを無効化しました。\n\n"
                f"**プレイヤー名:** {player.nickname}"
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PlayerCog(bot))