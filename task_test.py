from uuid import uuid4

from sidebrain_back.tasks.generate_track_task import generate_track_task
from sidebrain_back.tasks.knowledge_assessment_task import (
    prepare_knowledge_assessment_task,
)

# assessment real (chama Groq, ~30s)
task = prepare_knowledge_assessment_task.delay(
    str(uuid4()), "Python assíncrono", "Criar APIs com FastAPI", False
)
print(task.id, task.get(timeout=60))

# generation real (chama Groq + grava Track/Step/Lesson no postgres)
req = str(uuid4())
task2 = generate_track_task.delay(
    request_id=req,
    user_id=str(uuid4()),
    goal="Aprender Python",
    topic="Python",
)
print(task2.id, task2.get(timeout=120))
