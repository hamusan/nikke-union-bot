import discord
from discord import app_commands
from discord.ext import commands

from bot.core.logger import get_logger
from bot.exceptions import (
    DuplicateCharacterError,
    InvalidCharacterNameError,
    InvalidTeamMemberCountError,
    InvalidTeamNameError,
    PlayerInactiveError,
    PlayerNotFoundError,
    TeamAlreadyExistsError,
    TeamAlreadyInactiveError,
    TeamNotFoundError,
)
from bot.services import TeamService


logger = get_logger()


class TeamCog(commands.Cog):
    """編成管理用Discordコマンド。"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.team_service = TeamService()

    @app_commands.command(
        name="team-add",
        description="5人のNIKKE編成を登録します。",
    )
    @app_commands.describe(
        character1="1番目のNIKKE",
        character2="2番目のNIKKE",
        character3="3番目のNIKKE",
        character4="4番目のNIKKE",
        character5="5番目のNIKKE",
        memo="編成についてのメモ（省略可能）",
    )
    async def team_add(
        self,
        interaction: discord.Interaction,
        character1: str,
        character2: str,
        character3: str,
        character4: str,
        character5: str,
        memo: str | None = None,
    ) -> None:
        discord_id = str(interaction.user.id)

        character_names = [
            character1,
            character2,
            character3,
            character4,
            character5,
        ]

        try:
            team = self.team_service.create_team(
                discord_id=discord_id,
                discord_name=interaction.user.display_name,
                character_names=character_names,
                memo=memo,
            )

        except PlayerInactiveError:
            await interaction.response.send_message(
                "現在このプレイヤーは無効化されています。",
                ephemeral=True,
            )
            return

        except TeamAlreadyExistsError:
            await interaction.response.send_message(
                "同じ名前の編成がすでに登録されています。",
                ephemeral=True,
            )
            return

        except InvalidTeamNameError:
            await interaction.response.send_message(
                "編成名を入力してください。",
                ephemeral=True,
            )
            return

        except InvalidTeamMemberCountError:
            await interaction.response.send_message(
                "編成には5人のNIKKEが必要です。",
                ephemeral=True,
            )
            return

        except InvalidCharacterNameError:
            await interaction.response.send_message(
                "NIKKE名が空になっています。",
                ephemeral=True,
            )
            return

        except DuplicateCharacterError:
            await interaction.response.send_message(
                "同じNIKKEを1つの編成に複数登録することはできません。",
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                "Team creation failed: discord_id={}",
                discord_id,
            )

            await interaction.response.send_message(
                "編成登録中に予期しないエラーが発生しました。",
                ephemeral=True,
            )
            return

        member_lines = [
            f"{member.position}. {member.character.name}"
            for member in team.members
        ]

        logger.info(
            "Team created: team_id={}, player_id={}, name={}",
            team.id,
            team.player_id,
            team.team_name,
        )

        message = (
            f"**編成 #{team.team_no}** を登録しました。\n\n"
            + "\n".join(member_lines)
        )

        if team.memo:
            message += f"\n\nメモ: {team.memo}"

        await interaction.response.send_message(
            message,
            ephemeral=True,
        )

    @app_commands.command(
        name="team-list",
        description="自分の登録編成一覧を表示します。",
    )
    async def team_list(
        self,
        interaction: discord.Interaction,
    ) -> None:
        discord_id = str(interaction.user.id)

        try:
            teams = self.team_service.list_active_teams(
                discord_id
            )

        except PlayerNotFoundError:
            await interaction.response.send_message(
                (
                    "プレイヤー登録が見つかりません。\n"
                    "先に `/player-register` を実行してください。"
                ),
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                "Failed to get team list: discord_id={}",
                discord_id,
            )

            await interaction.response.send_message(
                "編成一覧の取得中にエラーが発生しました。",
                ephemeral=True,
            )
            return

        if not teams:
            await interaction.response.send_message(
                "現在登録されている編成はありません。",
                ephemeral=True,
            )
            return

        sections: list[str] = []

        for team in teams:
            member_lines = [
                f"{member.position}. {member.character.name}"
                for member in team.members
            ]

            section = (
                f"**編成 #{team.team_no}**\n"
                + "\n".join(member_lines)
            )

            if team.memo:
                section += f"\nメモ: {team.memo}"

            sections.append(section)

        message = (
            "**登録編成一覧**\n\n"
            + "\n\n".join(sections)
            + f"\n\n合計: **{len(teams)}編成**"
        )

        await interaction.response.send_message(
            message,
            ephemeral=True,
        )

    @app_commands.command(
        name="team-deactivate",
        description="自分の編成を無効化します。",
    )
    @app_commands.describe(
        team_no="無効化する編成番号",
    )
    async def team_deactivate(
        self,
        interaction: discord.Interaction,
        team_no: int
    ) -> None:
        discord_id = str(interaction.user.id)

        try:
            team = self.team_service.deactivate_team(
                discord_id=discord_id,
                team_no=team_no,
            )

        except PlayerNotFoundError:
            await interaction.response.send_message(
                "プレイヤー登録が見つかりません。",
                ephemeral=True,
            )
            return

        except TeamNotFoundError:
            await interaction.response.send_message(
                "指定された編成が見つかりません。",
                ephemeral=True,
            )
            return

        except TeamAlreadyInactiveError:
            await interaction.response.send_message(
                "その編成はすでに無効化されています。",
                ephemeral=True,
            )
            return

        except InvalidTeamNameError:
            await interaction.response.send_message(
                "編成名を入力してください。",
                ephemeral=True,
            )
            return

        except Exception:
            logger.exception(
                "Team deactivation failed: discord_id={}, team_name={}",
                discord_id,
                team_name,
            )

            await interaction.response.send_message(
                "編成の無効化中にエラーが発生しました。",
                ephemeral=True,
            )
            return

        logger.info(
            "Team deactivated: team_id={}, name={}",
            team.id,
            team.team_name,
        )

        await interaction.response.send_message(
            f"**編成 #{team.team_no}** を無効化しました。",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TeamCog(bot))