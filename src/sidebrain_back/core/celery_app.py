from celery import Celery

from sidebrain_back.core.constants import Env

celery_app = Celery(
    "worker",
    broker=f"redis://{Env.REDIS_HOST}:{Env.REDIS_PORT}/0",
    backend=f"redis://{Env.REDIS_HOST}:{Env.REDIS_PORT}/1",
    include=("sidebrain_back.tasks.knowledge_assessment_task",),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
)
