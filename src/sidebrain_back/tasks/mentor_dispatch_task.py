import asyncio

from sidebrain_back.core.celery_app import celery_app
from sidebrain_back.core.database import async_session, engine
from sidebrain_back.services.mentor_dispatch_service import (
    MentorDispatchService,
)
from sidebrain_back.tasks.mentor_generation_task import generate_mentor_task


async def _collect_pending() -> list[tuple[str, str]]:
    async with async_session() as db:
        return await MentorDispatchService(db).collect_pending()


@celery_app.task(name="tasks.dispatch_mentor", ignore_result=True)
def dispatch_mentor_task() -> None:
    async def run() -> list[tuple[str, str]]:
        try:
            return await _collect_pending()
        finally:
            await engine.dispose()

    for user_id, generation_id in asyncio.run(run()):
        generate_mentor_task.delay(user_id, generation_id)
