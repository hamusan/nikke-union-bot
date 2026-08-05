from bot.core.database import session_scope
from bot.exceptions import (
    PlayerAlreadyExistsError,
    PlayerAlreadyInactiveError,
    PlayerNotFoundError,
)
from bot.models.player import Player
from bot.repositories.player_repository import PlayerRepository


class PlayerService:
    """Playerに関するアプリケーション処理を担当する。"""

    def register_player(
        self,
        discord_id: str,
        nickname: str,
    ) -> Player:
        """新しいPlayerを登録する。"""

        with session_scope() as session:
            repository = PlayerRepository(session)

            existing_player = repository.get_by_discord_id(
                discord_id
            )

            if existing_player is not None:
                raise PlayerAlreadyExistsError(
                    f"Discord ID {discord_id} is already registered."
                )

            player = repository.create(
                discord_id=discord_id,
                nickname=nickname,
            )

            return player

    def get_player(
        self,
        discord_id: str,
    ) -> Player:
        """Discord IDからPlayerを取得する。"""

        with session_scope() as session:
            repository = PlayerRepository(session)

            player = repository.get_by_discord_id(
                discord_id
            )

            if player is None:
                raise PlayerNotFoundError(
                    f"Discord ID {discord_id} was not found."
                )

            return player

    def list_active_players(self) -> list[Player]:
        """有効なPlayer一覧を取得する。"""

        with session_scope() as session:
            repository = PlayerRepository(session)

            return repository.list_active()
    
    def deactivate_player(
        self,
        discord_id: str,
    ) -> Player:
        """Playerを無効化する。"""

        with session_scope() as session:
            repository = PlayerRepository(session)

            player = repository.get_by_discord_id(
                discord_id
            )

            if player is None:
                raise PlayerNotFoundError(
                    f"Discord ID {discord_id} was not found."
                )

            if not player.active:
                raise PlayerAlreadyInactiveError(
                    f"Discord ID {discord_id} is already inactive."
                )

            return repository.deactivate(player)