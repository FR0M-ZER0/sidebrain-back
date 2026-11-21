import asyncio
from uuid import UUID

from sidebrain_back.core.celery_app import celery_app
from sidebrain_back.core.database import async_session, engine
from sidebrain_back.services.mentor_generator_service import (
    MentorGeneratorService,
)
from sidebrain_back.services.mentor_processing_service import (
    MentorProcessingService,
)


@celery_app.task(name="tasks.generate_mentor", ignore_result=True)
def generate_mentor_task(user_id: str, generation_id: str) -> None:
    async def run() -> None:
        try:
            async with async_session() as db:
                service = MentorProcessingService(db, MentorGeneratorService())
                await service.process(UUID(user_id), UUID(generation_id))
        finally:
            await engine.dispose()

    asyncio.run(run())
