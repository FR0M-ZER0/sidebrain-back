import asyncio
from uuid import uuid4

from sqlalchemy import select

from sidebrain_back.core.database import async_session
from sidebrain_back.models.step_model import Step
from sidebrain_back.tasks.generate_track_task import generate_track_task
from sidebrain_back.tasks.knowledge_assessment_task import (
    prepare_knowledge_assessment_task,
)
from sidebrain_back.tasks.prepare_next_step_content_task import (
    prepare_next_step_content_task,
)


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
        # pega a última etapa (futura, sem conteúdo) em vez da primeira
        return str(ids[0] if len(ids) == 1 else ids[0])


# 1) assessment real (chama Groq, ~30s)
print("== 1) prepare_knowledge_assessment ==")
task = prepare_knowledge_assessment_task.delay(
    str(uuid4()), "Python assíncrono", "Criar APIs com FastAPI", False
)
print(task.id, task.get(timeout=60))

# 2) generation real (chama Groq + grava Track/Step/Lesson no postgres)
print("== 2) generate_track ==")
req = str(uuid4())
task2 = generate_track_task.delay(
    request_id=req,
    user_id=str(uuid4()),
    goal="Aprender Python",
    topic="Python",
)
result2 = task2.get(timeout=120)
print(task2.id, result2)

# 3) conteúdo incremental da próxima etapa (precisa de step_id real)
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
