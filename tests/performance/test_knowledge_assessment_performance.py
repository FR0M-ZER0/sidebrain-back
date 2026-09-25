import asyncio
import math
import os
from time import perf_counter
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from sidebrain_back.core.database import async_session, engine
from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.models.knowledge_assessment_model import (
    KnowledgeAssessment,
)
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.knowledge_assessment_repository import (
    KnowledgeAssessmentRepository,
)
from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentAcceptedResponse,
)
from sidebrain_back.services.knowledge_assessment_service import (
    get_knowledge_assessment_service,
)
from sidebrain_back.tasks.knowledge_assessment_task import (
    prepare_knowledge_assessment_task,
)


def _p95(samples: list[float]) -> float:
    if len(samples) < 100:
        raise ValueError("O cálculo de P95 exige pelo menos 100 amostras.")
    ordered = sorted(samples)
    return ordered[math.ceil(len(ordered) * 0.95) - 1]


class FastAcceptanceService:
    async def create_knowledge_assessment(self, _user, _payload):
        return AssessmentAcceptedResponse(
            assessment_id=uuid4(),
            status=KnowledgeAssessmentStatusEnum.PENDING,
        )


@pytest.mark.anyio
async def test_sc007_confirmation_p95_under_two_seconds_with_100_requests(
    test_app,
):
    test_app.dependency_overrides[get_knowledge_assessment_service] = (
        FastAcceptanceService
    )
    transport = httpx.ASGITransport(app=test_app)
    semaphore = asyncio.Semaphore(10)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:

        async def create(index: int):
            async with semaphore:
                started_at = perf_counter()
                response = await client.post(
                    "/api/v1/assessments",
                    json={"subject": f"Subject {index}"},
                )
                elapsed = perf_counter() - started_at
                return response, elapsed

        results = await asyncio.gather(
            *(create(index) for index in range(100))
        )

    responses = [response for response, _elapsed in results]
    samples = [elapsed for _response, elapsed in results]
    assert all(response.status_code == 202 for response in responses)
    assessment_ids = {
        response.json()["assessment_id"] for response in responses
    }
    assert len(assessment_ids) == 100
    assert _p95(samples) <= 2.0


@pytest.mark.anyio
async def test_sc008_real_worker_p95_under_thirty_seconds_for_100_assessments(
):
    if os.getenv("RUN_REAL_ASSESSMENT_PERFORMANCE") != "1":
        pytest.skip(
            "Requer PostgreSQL, Redis e worker Celery reais; execute com "
            "RUN_REAL_ASSESSMENT_PERFORMANCE=1."
        )

    user_id = uuid4()
    assessment_ids = [uuid4() for _ in range(100)]
    durations: dict = {}
    started_at = perf_counter()
    try:
        async with async_session() as db:
            db.add(
                User(
                    usr_id=user_id,
                    usr_email=f"{uuid4()}@example.com",
                    usr_name="Performance User",
                    usr_password_hash="test-hash",
                    usr_is_deleted=False,
                )
            )
            repository = KnowledgeAssessmentRepository(db)
            for index, assessment_id in enumerate(assessment_ids):
                await repository.create_pending(
                    assessment_id=assessment_id,
                    user_id=user_id,
                    subject=f"Performance {index}",
                    objective=None,
                    skip=True,
                    context_fingerprint=f"{index:064x}",
                )
            await db.commit()

        for index, assessment_id in enumerate(assessment_ids):
            prepare_knowledge_assessment_task.apply_async(
                kwargs={
                    "contract_version": 2,
                    "assessment_id": str(assessment_id),
                    "user_id": str(user_id),
                    "subject": f"Performance {index}",
                    "objective": None,
                    "skip": True,
                }
            )

        deadline = started_at + 30.0
        pending = set(assessment_ids)
        while pending and perf_counter() < deadline:
            async with async_session() as db:
                rows = await db.execute(
                    select(
                        KnowledgeAssessment.kas_id,
                        KnowledgeAssessment.kas_status,
                    ).where(KnowledgeAssessment.kas_id.in_(pending))
                )
                for assessment_id, assessment_status in rows:
                    if assessment_status in {
                        KnowledgeAssessmentStatusEnum.GENERATED,
                        KnowledgeAssessmentStatusEnum.SKIPPED,
                    }:
                        durations[assessment_id] = perf_counter() - started_at
                        pending.discard(assessment_id)
            if pending:
                await asyncio.sleep(0.05)

        assert not pending
        assert len(durations) == 100
        assert _p95(list(durations.values())) <= 30.0
    finally:
        async with async_session() as db:
            await db.execute(delete(User).where(User.usr_id == user_id))
            await db.commit()
        await engine.dispose()
