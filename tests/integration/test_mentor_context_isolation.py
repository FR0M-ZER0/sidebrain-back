from datetime import datetime
from uuid import uuid4

import pytest

from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.models.generation_request_model import GenerationRequest
from sidebrain_back.repositories.mentor_context_repository import (
    MentorContextRepository,
)


@pytest.mark.anyio
async def test_context_excludes_other_users_and_deleted_tracks(
    db_session,
    learning_hierarchy_factory,
    user_factory,
    quiz_factory,
    answer_factory,
):
    hierarchy = await learning_hierarchy_factory()
    second_hierarchy = await learning_hierarchy_factory()
    second_hierarchy.track.trk_user_id = hierarchy.user.usr_id
    await db_session.flush()
    other = await user_factory()
    quiz = await quiz_factory(hierarchy.lesson)
    await answer_factory(quiz, hierarchy.user, reason="Resposta do estudante")
    await answer_factory(quiz, other, reason="Dado de outra pessoa")
    other_quiz = await quiz_factory(second_hierarchy.lesson)
    await answer_factory(
        other_quiz, hierarchy.user, reason="Resposta de outra trilha"
    )
    repository = MentorContextRepository(db_session)

    context = await repository.get(
        hierarchy.user.usr_id, hierarchy.track.trk_id
    )
    assert context is not None
    assert "Resposta do estudante" in str(context)
    assert "Dado de outra pessoa" not in str(context)
    assert "Resposta de outra trilha" not in str(context)
    assert await repository.get(other.usr_id, hierarchy.track.trk_id) is None

    hierarchy.track.trk_is_deleted = True
    await db_session.flush()
    assert (
        await repository.get(hierarchy.user.usr_id, hierarchy.track.trk_id)
        is None
    )


@pytest.mark.anyio
async def test_context_uses_only_linked_assessment_and_marks_skipped(
    db_session, learning_hierarchy_factory, knowledge_assessment_factory
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    track_id = hierarchy.track.trk_id
    skipped = await knowledge_assessment_factory(
        owner=hierarchy.user,
        status=KnowledgeAssessmentStatusEnum.SKIPPED,
        skip=True,
    )
    repository = MentorContextRepository(db_session)
    context = await repository.get(user_id, track_id)
    assert "avaliacao_inicial" not in context

    request = GenerationRequest(
        request_id=uuid4(),
        user_id=user_id,
        context_fingerprint=uuid4().hex * 2,
        goal="Estudar Python",
        topic="Python",
        assessment_id=skipped.kas_id,
    )
    db_session.add(request)
    await db_session.flush()
    hierarchy.track.trk_generation_request_id = request.request_id
    await db_session.flush()

    context = await repository.get(user_id, track_id)
    assert context["avaliacao_inicial"]["estado"] == "skipped"
    assert context["avaliacao_inicial"]["nivel"] is None

    completed = await knowledge_assessment_factory(
        owner=hierarchy.user,
        status=KnowledgeAssessmentStatusEnum.COMPLETED,
    )
    completed.kas_completed_at = datetime(2020, 1, 1)
    request.assessment_id = completed.kas_id
    await db_session.flush()
    context = await repository.get(user_id, track_id)
    assert context["avaliacao_inicial"]["estado"] == "completed"
    assert context["avaliacao_inicial"]["data"].startswith("2020-01-01")


@pytest.mark.anyio
async def test_foreign_assessment_link_is_not_exposed(
    db_session,
    learning_hierarchy_factory,
    knowledge_assessment_factory,
    user_factory,
):
    hierarchy = await learning_hierarchy_factory()
    other = await user_factory()
    foreign = await knowledge_assessment_factory(owner=other)
    request = GenerationRequest(
        request_id=uuid4(),
        user_id=hierarchy.user.usr_id,
        context_fingerprint=uuid4().hex * 2,
        goal="Estudar Python",
        topic="Python",
        assessment_id=foreign.kas_id,
    )
    db_session.add(request)
    await db_session.flush()
    hierarchy.track.trk_generation_request_id = request.request_id
    await db_session.flush()
    context = await MentorContextRepository(db_session).get(
        hierarchy.user.usr_id, hierarchy.track.trk_id
    )
    assert "avaliacao_inicial" not in context
