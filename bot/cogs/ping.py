import discord
from discord import app_commands
from discord.ext import commands


class PingCog(commands.Cog):
    """Botの動作確認用コマンド。"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Botが正常に動作しているか確認します。",
    )
    async def ping(
        self,
        interaction: discord.Interaction,
    ) -> None:
        latency_ms = round(self.bot.latency * 1000)

        await interaction.response.send_message(
            f"Pong! 🏓 `{latency_ms} ms`"
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PingCog(bot))