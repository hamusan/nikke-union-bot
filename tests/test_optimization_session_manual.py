from sqlalchemy import (
    delete,
    select,
)

from bot.core.database import session_scope
from bot.models.optimization_session import (
    OptimizationSession,
)
from bot.models.raid import Raid
from bot.services.optimization.session_service import (
    OptimizationSessionService,
)


TEST_CHANNEL_ID = 9_999_990_001
TEST_MESSAGE_ID = 9_999_990_002
TEST_USER_ID = 9_999_990_003


def main() -> None:
    service = OptimizationSessionService()

    with session_scope() as session:
        raid_id = session.scalar(
            select(Raid.id)
            .where(
                Raid.active.is_(True)
            )
            .order_by(
                Raid.id.desc()
            )
        )

    if raid_id is None:
        raise RuntimeError(
            "Active Raidがありません。"
        )

    print(
        "Active Raid:",
        raid_id,
    )

    # --------------------------------
    # Start
    # --------------------------------

    state = service.start(
        channel_id=TEST_CHANNEL_ID,
        message_id=TEST_MESSAGE_ID,
        raid_id=raid_id,
        interval_minutes=5,
        started_by_discord_id=(
            TEST_USER_ID
        ),
    )

    print(
        "START:",
        state,
    )

    assert state.active
    assert (
        state.channel_id
        == TEST_CHANNEL_ID
    )

    # --------------------------------
    # Active一覧
    # --------------------------------

    active = service.list_active()

    found = any(
        item.channel_id
        == TEST_CHANNEL_ID
        for item in active
    )

    assert found

    print(
        "LIST ACTIVE: OK"
    )

    # --------------------------------
    # Stop
    # --------------------------------

    stopped = service.stop(
        TEST_CHANNEL_ID
    )

    assert stopped is not None
    assert not stopped.active

    print(
        "STOP: OK"
    )

    # --------------------------------
    # Test row削除
    # --------------------------------

    with session_scope() as session:
        session.execute(
            delete(
                OptimizationSession
            ).where(
                OptimizationSession.channel_id
                == TEST_CHANNEL_ID
            )
        )

    print(
        "CLEANUP: OK"
    )

    print()
    print(
        "Optimization Session TEST OK"
    )


if __name__ == "__main__":
    main()