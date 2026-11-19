import asyncio

import pytest
from sqlalchemy import text

from sidebrain_back.core.database import async_session, engine
from sidebrain_back.core.job_notifications import JobNotificationListener


@pytest.mark.anyio
async def test_listener_only_delivers_notifications_after_commit():
    listener = JobNotificationListener()
    await listener.start()
    event = listener.subscribe("assessment:test-resource")
    try:
        async with async_session() as session:
            await session.execute(
                text(
                    "SELECT pg_notify('sidebrain_job_updates', "
                    "'assessment:test-resource')"
                )
            )
            await session.rollback()
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(event.wait(), timeout=0.05)

        event.clear()
        async with async_session() as session:
            await session.execute(
                text(
                    "SELECT pg_notify('sidebrain_job_updates', "
                    "'assessment:test-resource')"
                )
            )
            await session.commit()
        await asyncio.wait_for(event.wait(), timeout=1)
    finally:
        listener.unsubscribe("assessment:test-resource", event)
        await listener.close()
        await engine.dispose()

    assert not listener._subscribers
