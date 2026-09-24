import asyncio
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import delete, event

from sidebrain_back.core.database import async_session, engine
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.knowledge_assessment_repository import (
    KnowledgeAssessmentRepository,
)
from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentAnswerInput,
    AssessmentAnswersRequest,
    AssessmentCreateRequest,
    GeneratedAssessmentPayload,
)
from sidebrain_back.services.knowledge_assessment_service import (
    KnowledgeAssessmentService,
    get_knowledge_assessment_service,
)


def _generated_payload() -> GeneratedAssessmentPayload:
    return GeneratedAssessmentPayload.model_validate(
        {
            "questions": [
                {
                    "id": f"provider-question-{question}",
                    "statement": f"Pergunta {question}",
                    "alternatives": [
                        {
                            "id": f"provider-{question}-{alternative}",
                            "text": f"Alternativa {alternative}",
                        }
                        for alternative in range(1, 5)
                    ],
                    "correct_alternative_id": f"provider-{question}-1",
                }
                for question in range(1, 6)
            ]
        }
    )


class DeterministicGenerator:
    def __init__(self) -> None:
        self.calls = []

    def generate(self, subject, objective=None):
        self.calls.append((subject, objective))
        return _generated_payload()


@pytest.mark.anyio
async def test_pending_to_generated_persists_complete_public_hierarchy(
    db_session,
    knowledge_assessment_factory,
):
    assessment = await knowledge_assessment_factory()
    repository = KnowledgeAssessmentRepository(db_session)
    generator = DeterministicGenerator()
    service = KnowledgeAssessmentService(
        generator,
        repository=repository,
        db=db_session,
    )

    pending = await service.get_knowledge_assessment(
        SimpleNamespace(usr_id=assessment.kas_user_id),
        assessment.kas_id,
    )
    assert pending.status is KnowledgeAssessmentStatusEnum.PENDING
    assert pending.questions == []

    status = await service.process_persisted_assessment(
        assessment_id=assessment.kas_id,
        user_id=assessment.kas_user_id,
        subject=assessment.kas_subject,
        objective=assessment.kas_objective,
        skip=False,
    )

    assert status is KnowledgeAssessmentStatusEnum.GENERATED
    generated = await service.get_knowledge_assessment(
        SimpleNamespace(usr_id=assessment.kas_user_id),
        assessment.kas_id,
    )
    assert len(generated.questions) == 5
    assert all(
        len(question.alternatives) == 4
        for question in generated.questions
    )
    public = generated.model_dump(mode="json")
    assert "is_correct" not in str(public)
    assert "correct_alternative_id" not in str(public)
    assert generated.score is None
    assert generated.level is None
    persisted = await repository.get_accessible(
        assessment.kas_id, assessment.kas_user_id
    )
    assert persisted is not None
    assert sum(
        alternative.kaa_is_correct
        for question in persisted.questions
        for alternative in question.alternatives
    ) == 5

    second_generator = DeterministicGenerator()
    redelivery_service = KnowledgeAssessmentService(
        second_generator,
        repository=repository,
        db=db_session,
    )
    redelivered_status = await redelivery_service.process_persisted_assessment(
        assessment_id=assessment.kas_id,
        user_id=assessment.kas_user_id,
        subject=assessment.kas_subject,
        objective=assessment.kas_objective,
        skip=False,
    )
    assert redelivered_status is KnowledgeAssessmentStatusEnum.GENERATED
    assert second_generator.calls == []


@pytest.mark.anyio
async def test_invalid_generation_marks_failed_without_children(
    db_session,
    knowledge_assessment_factory,
):
    assessment = await knowledge_assessment_factory()
    repository = KnowledgeAssessmentRepository(db_session)
    service = KnowledgeAssessmentService(repository=repository, db=db_session)

    await service.fail_preparation(
        assessment_id=assessment.kas_id,
        user_id=assessment.kas_user_id,
        error_code="invalid_generation_result",
    )

    failed = await service.get_knowledge_assessment(
        SimpleNamespace(usr_id=assessment.kas_user_id),
        assessment.kas_id,
    )
    assert failed.status is KnowledgeAssessmentStatusEnum.FAILED
    assert failed.error_code == "invalid_generation_result"
    assert failed.questions == []


@pytest.mark.anyio
async def test_repeated_active_creation_returns_one_id_and_one_publication(
    db_session,
    authenticated_user,
):
    db_session.add(authenticated_user)
    await db_session.flush()
    repository = KnowledgeAssessmentRepository(db_session)
    publisher = SimpleNamespace(apply_async=lambda **_kwargs: None)
    service = KnowledgeAssessmentService(
        repository=repository,
        db=db_session,
        publisher=publisher,
    )
    user = authenticated_user
    payload = AssessmentCreateRequest(
        subject="  Python  ",
        objective="  FastAPI  ",
    )
    publications = []
    publisher.apply_async = lambda **kwargs: publications.append(kwargs)

    first = await service.create_knowledge_assessment(user, payload)
    second = await service.create_knowledge_assessment(user, payload)

    assert first.assessment_id == second.assessment_id
    assert len(publications) == 1


def _answers_for_hierarchy(hierarchy, correct_count=5):
    return AssessmentAnswersRequest(
        answers=[
            AssessmentAnswerInput(
                question_id=question.kaq_id,
                alternative_id=(
                    hierarchy.correct_alternatives[index].kaa_id
                    if index < correct_count
                    else next(
                        alternative.kaa_id
                        for alternative in hierarchy.incorrect_alternatives
                        if alternative.kaa_question_id == question.kaq_id
                    )
                ),
            )
            for index, question in enumerate(hierarchy.questions)
        ]
    )


@pytest.mark.anyio
async def test_submission_persists_five_answers_score_and_level_atomically(
    db_session,
    knowledge_assessment_hierarchy_factory,
):
    hierarchy = await knowledge_assessment_hierarchy_factory()
    await db_session.commit()
    assessment_id = hierarchy.assessment.kas_id
    owner_id = hierarchy.owner.usr_id
    repository = KnowledgeAssessmentRepository(db_session)
    service = KnowledgeAssessmentService(repository=repository, db=db_session)

    result = await service.submit_knowledge_assessment_answers(
        hierarchy.owner,
        hierarchy.assessment.kas_id,
        _answers_for_hierarchy(hierarchy, correct_count=4),
    )

    assert result.status is KnowledgeAssessmentStatusEnum.COMPLETED
    assert result.score == 4
    assert result.level.value == "advanced"
    persisted = await repository.get_accessible(
        assessment_id,
        owner_id,
    )
    assert persisted is not None
    assert len(persisted.answers) == 5
    assert len({answer.kar_question_id for answer in persisted.answers}) == 5


@pytest.mark.anyio
async def test_invalid_cross_question_selection_rolls_back_everything(
    db_session,
    knowledge_assessment_hierarchy_factory,
):
    hierarchy = await knowledge_assessment_hierarchy_factory()
    await db_session.commit()
    assessment_id = hierarchy.assessment.kas_id
    owner_id = hierarchy.owner.usr_id
    repository = KnowledgeAssessmentRepository(db_session)
    service = KnowledgeAssessmentService(repository=repository, db=db_session)
    payload = _answers_for_hierarchy(hierarchy)
    payload.answers[0].alternative_id = (
        hierarchy.correct_alternatives[1].kaa_id
    )

    with pytest.raises(ProblemDetailError) as raised:
        await service.submit_knowledge_assessment_answers(
            hierarchy.owner,
            hierarchy.assessment.kas_id,
            payload,
        )

    assert raised.value.status_code == 422
    persisted = await repository.get_accessible(
        assessment_id,
        owner_id,
    )
    assert persisted is not None
    assert persisted.kas_status is KnowledgeAssessmentStatusEnum.GENERATED
    assert persisted.answers == []


@pytest.mark.anyio
async def test_two_concurrent_submissions_preserve_first_result():
    user_id = uuid4()
    assessment_id = uuid4()
    try:
        async with async_session() as seed_db:
            seed_db.add(
                User(
                    usr_id=user_id,
                    usr_email=f"{uuid4()}@example.com",
                    usr_name="Concurrent User",
                    usr_password_hash="test-hash",
                    usr_is_deleted=False,
                )
            )
            repository = KnowledgeAssessmentRepository(seed_db)
            assessment = await repository.create_pending(
                assessment_id=assessment_id,
                user_id=user_id,
                subject="Python",
                objective=None,
                skip=False,
                context_fingerprint=uuid4().hex * 2,
            )
            await repository.mark_generated(
                assessment, _generated_payload()
            )
            await seed_db.commit()
            seeded = await repository.get_accessible(
                assessment_id, user_id
            )
            assert seeded is not None
            payload = AssessmentAnswersRequest(
                answers=[
                    AssessmentAnswerInput(
                        question_id=question.kaq_id,
                        alternative_id=question.alternatives[0].kaa_id,
                    )
                    for question in seeded.questions
                ]
            )

        async def submit_once():
            async with async_session() as worker_db:
                service = KnowledgeAssessmentService(
                    repository=KnowledgeAssessmentRepository(worker_db),
                    db=worker_db,
                )
                return await service.submit_knowledge_assessment_answers(
                    SimpleNamespace(usr_id=user_id),
                    assessment_id,
                    payload,
                )

        results = await asyncio.gather(
            submit_once(), submit_once(), return_exceptions=True
        )

        successes = [
            result for result in results if not isinstance(result, Exception)
        ]
        conflicts = [
            result
            for result in results
            if isinstance(result, ProblemDetailError)
            and result.status_code == 409
        ]
        assert len(successes) == 1
        assert len(conflicts) == 1

        async with async_session() as verify_db:
            persisted = await KnowledgeAssessmentRepository(
                verify_db
            ).get_accessible(assessment_id, user_id)
            assert persisted is not None
            assert (
                persisted.kas_status
                is KnowledgeAssessmentStatusEnum.COMPLETED
            )
            assert persisted.kas_score == 5
            assert len(persisted.answers) == 5
    finally:
        async with async_session() as cleanup_db:
            await cleanup_db.execute(
                delete(User).where(User.usr_id == user_id)
            )
            await cleanup_db.commit()
        await engine.dispose()


@pytest.mark.anyio
async def test_completed_get_has_stable_order_constant_queries_and_ownership(
    db_session,
    knowledge_assessment_hierarchy_factory,
):
    hierarchy = await knowledge_assessment_hierarchy_factory()
    await db_session.commit()
    assessment_id = hierarchy.assessment.kas_id
    owner_id = hierarchy.owner.usr_id
    other_user_id = hierarchy.other_user.usr_id
    repository = KnowledgeAssessmentRepository(db_session)
    service = KnowledgeAssessmentService(repository=repository, db=db_session)
    await service.submit_knowledge_assessment_answers(
        hierarchy.owner,
        assessment_id,
        _answers_for_hierarchy(hierarchy, correct_count=3),
    )
    db_session.expire_all()

    selects = []

    def count_selects(
        _connection,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", count_selects)
    try:
        detail = await service.get_knowledge_assessment(
            SimpleNamespace(usr_id=owner_id), assessment_id
        )
    finally:
        event.remove(
            engine.sync_engine, "before_cursor_execute", count_selects
        )

    assert detail.status is KnowledgeAssessmentStatusEnum.COMPLETED
    assert len(selects) == 4
    assert [question.statement for question in detail.questions] == [
        f"Pergunta {position}?" for position in range(1, 6)
    ]
    assert all(
        [alternative.text for alternative in question.alternatives]
        == [f"Alternativa {position}" for position in range(1, 5)]
        for question in detail.questions
    )

    with pytest.raises(ProblemDetailError) as unowned:
        await service.get_knowledge_assessment(
            SimpleNamespace(usr_id=other_user_id), assessment_id
        )
    with pytest.raises(ProblemDetailError) as missing:
        await service.get_knowledge_assessment(
            SimpleNamespace(usr_id=owner_id), uuid4()
        )
    assert unowned.value.status_code == missing.value.status_code == 404
    assert unowned.value.detail == missing.value.detail


@pytest.mark.anyio
async def test_public_end_to_end_create_generate_answer_and_get_completed(
    test_app,
    db_session,
    authenticated_user,
):
    db_session.add(authenticated_user)
    await db_session.commit()
    published = []
    publisher = SimpleNamespace(
        apply_async=lambda **kwargs: published.append(kwargs)
    )
    repository = KnowledgeAssessmentRepository(db_session)
    service = KnowledgeAssessmentService(
        DeterministicGenerator(),
        repository=repository,
        db=db_session,
        publisher=publisher,
    )
    test_app.dependency_overrides[get_knowledge_assessment_service] = (
        lambda: service
    )
    transport = httpx.ASGITransport(app=test_app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        created = await client.post(
            "/api/v1/assessments",
            json={
                "subject": "Python",
                "objective": "FastAPI",
                "skip": False,
            },
        )
        assert created.status_code == 202
        assessment_id = UUID(created.json()["assessment_id"])
        assert len(published) == 1

        kwargs = published[0]["kwargs"]
        status = await service.process_persisted_assessment(
            assessment_id=assessment_id,
            user_id=authenticated_user.usr_id,
            subject=kwargs["subject"],
            objective=kwargs["objective"],
            skip=kwargs["skip"],
        )
        assert status is KnowledgeAssessmentStatusEnum.GENERATED

        generated = await client.get(
            f"/api/v1/assessments/{assessment_id}"
        )
        assert generated.status_code == 200
        questions = generated.json()["questions"]
        assert len(questions) == 5
        assert all(
            len(question["alternatives"]) == 4 for question in questions
        )
        assert all(
            isinstance(UUID(question["id"]), UUID)
            and all(
                isinstance(UUID(alternative["id"]), UUID)
                for alternative in question["alternatives"]
            )
            for question in questions
        )
        assert all(
            not question["id"].startswith("provider-")
            for question in questions
        )

        completed = await client.post(
            f"/api/v1/assessments/{assessment_id}/answers",
            json={
                "answers": [
                    {
                        "question_id": question["id"],
                        "alternative_id": question["alternatives"][0]["id"],
                    }
                    for question in questions
                ]
            },
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "completed"
        assert completed.json()["score"] == 5
        assert completed.json()["level"] == "pro"

        final = await client.get(f"/api/v1/assessments/{assessment_id}")
        assert final.status_code == 200
        assert final.json()["status"] == "completed"
        assert final.json()["level"] == "pro"
