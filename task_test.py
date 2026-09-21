import asyncio
from uuid import uuid4

from sqlalchemy import select

from sidebrain_back.core.database import async_session
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.user_model import User
from sidebrain_back.tasks.generate_track_task import generate_track_task
from sidebrain_back.tasks.knowledge_assessment_task import (
    prepare_knowledge_assessment_task,
)
from sidebrain_back.tasks.prepare_next_step_content_task import (
    prepare_next_step_content_task,
)


async def get_existing_user_id() -> str | None:
    async with async_session() as db:
        result = await db.execute(select(User.usr_id).limit(1))
        user_id = result.scalars().first()
        return str(user_id) if user_id else None


async def get_future_step_id(track_id: str) -> str | None:
    async with async_session() as db:
        result = await db.execute(
            select(Step.stp_id)
            .where(
                Step.stp_track_id == track_id,
                Step.stp_is_deleted.is_(False),
            )
            .order_by(Step.stp_updated_at.desc(), Step.stp_id.desc())
        )
        ids = list(result.scalars().all())
        if not ids:
            return None
        return str(ids[0] if len(ids) == 1 else ids[0])


print("== 1) prepare_knowledge_assessment ==")
task = prepare_knowledge_assessment_task.delay(
    str(uuid4()), "Python assíncrono", "Criar APIs com FastAPI", False
)
print(task.id, task.get(timeout=60))

print("== 2) generate_track ==")
user_id = asyncio.run(get_existing_user_id())
if not user_id:
    print("nenhum usuário no banco (rode seed.py), pulando etapas 2 e 3")
    result2 = {"status": "skipped", "reason": "no_user_in_db"}
else:
    print("user_id:", user_id)
    req = str(uuid4())
    task2 = generate_track_task.delay(
        request_id=req,
        user_id=user_id,
        goal="Aprender Python",
        topic="Python",
    )
    result2 = task2.get(timeout=120)
    print(task2.id, result2)

print("== 3) prepare_next_step_content ==")
track_id = result2.get("track_id") if isinstance(result2, dict) else None
if not track_id:
    print("generate_track não retornou track_id, pulando etapa 3:", result2)
else:
    step_id = asyncio.run(get_future_step_id(track_id))
    print("track_id:", track_id, "step_id:", step_id)
    if not step_id:
        print("nenhuma etapa encontrada para a trilha")
    else:
        task3 = prepare_next_step_content_task.delay(step_id)
        print(task3.id, task3.get(timeout=120))
