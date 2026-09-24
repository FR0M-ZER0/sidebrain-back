from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.repositories.knowledge_assessment_repository import (
    KnowledgeAssessmentRepository,
)


def _compiled(statement) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


@pytest.mark.anyio
async def test_create_pending_adds_and_flushes_assessment():
    db = MagicMock()
    db.flush = AsyncMock()
    repository = KnowledgeAssessmentRepository(db)
    assessment_id = uuid4()
    user_id = uuid4()

    assessment = await repository.create_pending(
        assessment_id=assessment_id,
        user_id=user_id,
        subject="Python",
        objective="Fundamentos",
        skip=False,
        context_fingerprint="a" * 64,
    )

    assert assessment.kas_id == assessment_id
    assert assessment.kas_user_id == user_id
    assert assessment.kas_status is KnowledgeAssessmentStatusEnum.PENDING
    db.add.assert_called_once_with(assessment)
    db.flush.assert_awaited_once()


@pytest.mark.anyio
async def test_get_filters_by_assessment_id():
    db = MagicMock()
    expected = object()
    db.scalar = AsyncMock(return_value=expected)
    repository = KnowledgeAssessmentRepository(db)
    assessment_id = uuid4()

    assert await repository.get(assessment_id) is expected

    sql = _compiled(db.scalar.await_args.args[0])
    assert "knowledge_assessment.kas_id" in sql
    assert str(assessment_id) in sql


@pytest.mark.anyio
async def test_get_active_by_fingerprint_filters_owner_and_active_states():
    db = MagicMock()
    db.scalar = AsyncMock(return_value=None)
    repository = KnowledgeAssessmentRepository(db)
    user_id = uuid4()

    await repository.get_active_by_fingerprint(user_id, "b" * 64)

    sql = _compiled(db.scalar.await_args.args[0])
    assert str(user_id) in sql
    assert "kas_context_fingerprint" in sql
    assert "pending" in sql
    assert "generated" in sql


@pytest.mark.anyio
async def test_get_accessible_filters_assessment_and_owner_together():
    db = MagicMock()
    result = MagicMock()
    scalar_result = result.scalars.return_value.unique.return_value
    scalar_result.one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    repository = KnowledgeAssessmentRepository(db)
    assessment_id = uuid4()
    user_id = uuid4()

    await repository.get_accessible(assessment_id, user_id)

    statement = db.execute.await_args.args[0]
    sql = _compiled(statement)
    assert str(assessment_id) in sql
    assert str(user_id) in sql
    assert "kas_id" in sql and "kas_user_id" in sql


@pytest.mark.anyio
async def test_accessible_query_uses_batched_hierarchy_loading():
    db = MagicMock()
    result = MagicMock()
    scalar_result = result.scalars.return_value.unique.return_value
    scalar_result.one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    repository = KnowledgeAssessmentRepository(db)

    await repository.get_accessible(uuid4(), uuid4())

    statement = db.execute.await_args.args[0]
    assert len(statement._with_options) == 2
    assert all(
        "Load" in type(option).__name__
        for option in statement._with_options
    )
    db.execute.assert_awaited_once()


@pytest.mark.anyio
async def test_get_for_update_filters_owner_and_emits_lock():
    db = MagicMock()
    result = MagicMock()
    scalar_result = result.scalars.return_value.unique.return_value
    scalar_result.one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    repository = KnowledgeAssessmentRepository(db)
    assessment_id = uuid4()
    user_id = uuid4()

    await repository.get_for_update(assessment_id, user_id)

    statement = db.execute.await_args.args[0]
    sql = _compiled(statement)
    assert str(assessment_id) in sql
    assert str(user_id) in sql
    assert "FOR UPDATE" in sql
    assert len(statement._with_options) == 2
