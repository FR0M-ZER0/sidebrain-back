from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.models.knowledge_assessment_alternative_model import (
    KnowledgeAssessmentAlternative,
)
from sidebrain_back.models.knowledge_assessment_model import (
    KnowledgeAssessment,
)
from sidebrain_back.models.knowledge_assessment_question_model import (
    KnowledgeAssessmentQuestion,
)
from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentAnswerInput,
    AssessmentAnswersRequest,
    AssessmentContext,
    AssessmentCreateRequest,
    KnowledgeAssessmentResult,
)
from sidebrain_back.services.knowledge_assessment_service import (
    KnowledgeAssessmentService,
)


def _question(number: str) -> dict:
    return {
        "id": f"q{number}",
        "statement": f"Pergunta {number} sobre o assunto.",
        "alternatives": [
            {"id": "a", "text": "Alternativa A"},
            {"id": "b", "text": "Alternativa B"},
            {"id": "c", "text": "Alternativa C"},
            {"id": "d", "text": "Alternativa D"},
        ],
    }


def _valid_generated_result() -> dict:
    return {
        "assessment_id": str(uuid4()),
        "status": "generated",
        "level": None,
        "questions": [_question(str(index)) for index in range(1, 6)],
    }


class FakeGenerator:
    def __init__(self, payload: dict | None = None):
        self.payload = payload or _valid_generated_result()
        self.calls: list[tuple[str | None, str | None]] = []

    def generate(self, subject: str, objective: str | None = None) -> dict:
        self.calls.append((subject, objective))
        return self.payload


def test_service_generates_assessment_for_valid_subject():
    generator = FakeGenerator()
    service = KnowledgeAssessmentService(generator)

    result = service.prepare_assessment(
        AssessmentContext(
            user_id=str(uuid4()),
            subject="Python assíncrono",
            objective="Criar APIs com FastAPI",
            skip=False,
        )
    )

    assert isinstance(result, KnowledgeAssessmentResult)
    assert result.status == "generated"
    assert len(result.questions) == 5
    assert generator.calls == [("Python assíncrono", "Criar APIs com FastAPI")]


def test_service_rejects_blank_subject_when_not_skipping():
    service = KnowledgeAssessmentService(FakeGenerator())

    with pytest.raises(ValueError):
        service.prepare_assessment(
            AssessmentContext(
                user_id=str(uuid4()),
                subject="   ",
                objective="Objetivo opcional",
                skip=False,
            )
        )


def test_service_returns_skip_result_without_calling_provider():
    generator = FakeGenerator()
    service = KnowledgeAssessmentService(generator)

    result = service.prepare_assessment(
        AssessmentContext(
            user_id=str(uuid4()),
            subject="Ignorado",
            objective="Ignorado",
            skip=True,
        )
    )

    assert result.status == "skipped"
    assert result.level == "beginner"
    assert result.questions == []
    assert generator.calls == []


def _assessment(user_id, status=KnowledgeAssessmentStatusEnum.PENDING):
    return KnowledgeAssessment(
        kas_id=uuid4(),
        kas_user_id=user_id,
        kas_subject="Python",
        kas_objective="FastAPI",
        kas_skip=False,
        kas_context_fingerprint="a" * 64,
        kas_status=status,
    )


def _async_service(*, existing=None, created=None):
    repository = MagicMock()
    repository.get_active_by_fingerprint = AsyncMock(return_value=existing)
    repository.create_pending = AsyncMock(return_value=created)
    repository.mark_failed = AsyncMock(return_value=True)
    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    publisher = MagicMock()
    service = KnowledgeAssessmentService(
        repository=repository,
        db=db,
        publisher=publisher,
    )
    return service, repository, db, publisher


def test_context_fingerprint_is_canonical_after_schema_normalization():
    first = AssessmentCreateRequest(
        subject="  Python  ", objective="  FastAPI  ", skip=False
    )
    second = AssessmentCreateRequest(
        subject="Python", objective="FastAPI", skip=False
    )

    assert KnowledgeAssessmentService.context_fingerprint(first) == (
        KnowledgeAssessmentService.context_fingerprint(second)
    )
    assert len(KnowledgeAssessmentService.context_fingerprint(first)) == 64


def test_context_fingerprint_distinguishes_skip_choice():
    generated = AssessmentCreateRequest(subject="Python", skip=False)
    skipped = AssessmentCreateRequest(subject="Python", skip=True)

    assert KnowledgeAssessmentService.context_fingerprint(generated) != (
        KnowledgeAssessmentService.context_fingerprint(skipped)
    )


@pytest.mark.anyio
async def test_create_persists_canonical_id_before_named_v2_enqueue():
    user = SimpleNamespace(usr_id=uuid4())
    created = _assessment(user.usr_id)
    service, repository, db, publisher = _async_service(created=created)
    events = []
    db.commit.side_effect = lambda: events.append("commit")
    publisher.apply_async.side_effect = lambda **_kwargs: events.append(
        "publish"
    )

    result = await service.create_knowledge_assessment(
        user,
        AssessmentCreateRequest(subject=" Python ", objective=" FastAPI "),
    )

    assert result.assessment_id == created.kas_id
    assert result.status is KnowledgeAssessmentStatusEnum.PENDING
    assert events == ["commit", "publish"]
    kwargs = publisher.apply_async.call_args.kwargs["kwargs"]
    assert kwargs == {
        "contract_version": 2,
        "assessment_id": str(created.kas_id),
        "user_id": str(user.usr_id),
        "subject": "Python",
        "objective": "FastAPI",
        "skip": False,
    }
    repository.create_pending.assert_awaited_once()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "status",
    [
        KnowledgeAssessmentStatusEnum.PENDING,
        KnowledgeAssessmentStatusEnum.GENERATED,
    ],
)
async def test_create_reuses_active_context_without_new_publish(status):
    user = SimpleNamespace(usr_id=uuid4())
    existing = _assessment(user.usr_id, status)
    service, repository, db, publisher = _async_service(existing=existing)

    result = await service.create_knowledge_assessment(
        user, AssessmentCreateRequest(subject="Python", objective="FastAPI")
    )

    assert result.assessment_id == existing.kas_id
    assert result.status is status
    repository.create_pending.assert_not_awaited()
    db.commit.assert_not_awaited()
    publisher.apply_async.assert_not_called()


@pytest.mark.anyio
async def test_create_after_terminal_state_creates_a_new_assessment():
    user = SimpleNamespace(usr_id=uuid4())
    created = _assessment(user.usr_id)
    service, repository, _db, publisher = _async_service(created=created)

    result = await service.create_knowledge_assessment(
        user, AssessmentCreateRequest(subject="Python", objective="FastAPI")
    )

    assert result.assessment_id == created.kas_id
    repository.create_pending.assert_awaited_once()
    publisher.apply_async.assert_called_once()


@pytest.mark.anyio
async def test_concurrent_unique_violation_reuses_winning_assessment():
    user = SimpleNamespace(usr_id=uuid4())
    winner = _assessment(user.usr_id)
    service, repository, db, publisher = _async_service()
    repository.get_active_by_fingerprint.side_effect = [None, winner]
    repository.create_pending.side_effect = IntegrityError(
        "insert", {}, Exception("unique")
    )

    result = await service.create_knowledge_assessment(
        user, AssessmentCreateRequest(subject="Python", objective="FastAPI")
    )

    assert result.assessment_id == winner.kas_id
    db.rollback.assert_awaited_once()
    publisher.apply_async.assert_not_called()


@pytest.mark.anyio
async def test_publish_failure_marks_created_assessment_failed_and_returns_503(
):
    user = SimpleNamespace(usr_id=uuid4())
    created = _assessment(user.usr_id)
    service, repository, db, publisher = _async_service(created=created)
    publisher.apply_async.side_effect = RuntimeError("broker secret")

    with pytest.raises(ProblemDetailError) as raised:
        await service.create_knowledge_assessment(
            user,
            AssessmentCreateRequest(subject="Python", objective="FastAPI"),
        )

    assert raised.value.status_code == 503
    repository.mark_failed.assert_awaited_once_with(
        created, "generation_failed"
    )
    assert db.commit.await_count == 2


def _generated_assessment(user_id):
    now = datetime.now(UTC).replace(tzinfo=None)
    assessment = KnowledgeAssessment(
        kas_id=uuid4(),
        kas_user_id=user_id,
        kas_subject="Python",
        kas_objective=None,
        kas_skip=False,
        kas_context_fingerprint="c" * 64,
        kas_status=KnowledgeAssessmentStatusEnum.GENERATED,
        kas_created_at=now,
        kas_updated_at=now,
    )
    assessment.questions = []
    for question_position in range(1, 6):
        question = KnowledgeAssessmentQuestion(
            kaq_id=uuid4(),
            kaq_assessment_id=assessment.kas_id,
            kaq_statement=f"Pergunta {question_position}",
            kaq_position=question_position,
        )
        question.alternatives = [
            KnowledgeAssessmentAlternative(
                kaa_id=uuid4(),
                kaa_question_id=question.kaq_id,
                kaa_text=f"Alternativa {alternative_position}",
                kaa_position=alternative_position,
                kaa_is_correct=alternative_position == 1,
            )
            for alternative_position in range(1, 5)
        ]
        assessment.questions.append(question)
    assessment.answers = []
    return assessment


def _answer_request(assessment, correct_count):
    return AssessmentAnswersRequest(
        answers=[
            AssessmentAnswerInput(
                question_id=question.kaq_id,
                alternative_id=question.alternatives[
                    0 if index < correct_count else 1
                ].kaa_id,
            )
            for index, question in enumerate(assessment.questions)
        ]
    )


def _submission_service(assessment):
    repository = MagicMock()
    repository.get_for_update = AsyncMock(return_value=assessment)

    async def complete(target, answers, *, score, level):
        target.kas_status = KnowledgeAssessmentStatusEnum.COMPLETED
        target.kas_score = score
        target.kas_level = level
        target.kas_completed_at = datetime.now(UTC).replace(tzinfo=None)
        target.kas_updated_at = target.kas_completed_at

    repository.complete = AsyncMock(side_effect=complete)
    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    service = KnowledgeAssessmentService(repository=repository, db=db)
    return service, repository, db


@pytest.mark.anyio
@pytest.mark.parametrize(
    "correct_count,expected_level",
    [
        (0, "beginner"),
        (1, "beginner"),
        (2, "intermediate"),
        (3, "intermediate"),
        (4, "advanced"),
        (5, "pro"),
    ],
)
async def test_submit_calculates_all_score_cutoffs(
    correct_count, expected_level
):
    user = SimpleNamespace(usr_id=uuid4())
    assessment = _generated_assessment(user.usr_id)
    service, repository, db = _submission_service(assessment)

    result = await service.submit_knowledge_assessment_answers(
        user,
        assessment.kas_id,
        _answer_request(assessment, correct_count),
    )

    assert result.score == correct_count
    assert result.level.value == expected_level
    repository.complete.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_submit_rejects_incomplete_question_set_without_mutation():
    user = SimpleNamespace(usr_id=uuid4())
    assessment = _generated_assessment(user.usr_id)
    service, repository, db = _submission_service(assessment)
    request = _answer_request(assessment, 5)
    request.answers[0].question_id = uuid4()

    with pytest.raises(ProblemDetailError) as raised:
        await service.submit_knowledge_assessment_answers(
            user, assessment.kas_id, request
        )

    assert raised.value.status_code == 422
    repository.complete.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_submit_rejects_alternative_from_another_question():
    user = SimpleNamespace(usr_id=uuid4())
    assessment = _generated_assessment(user.usr_id)
    service, repository, db = _submission_service(assessment)
    request = _answer_request(assessment, 5)
    request.answers[0].alternative_id = (
        assessment.questions[1].alternatives[0].kaa_id
    )

    with pytest.raises(ProblemDetailError) as raised:
        await service.submit_knowledge_assessment_answers(
            user, assessment.kas_id, request
        )

    assert raised.value.status_code == 422
    repository.complete.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "state",
    [
        KnowledgeAssessmentStatusEnum.PENDING,
        KnowledgeAssessmentStatusEnum.SKIPPED,
        KnowledgeAssessmentStatusEnum.COMPLETED,
        KnowledgeAssessmentStatusEnum.FAILED,
    ],
)
async def test_submit_rejects_incompatible_or_terminal_state(state):
    user = SimpleNamespace(usr_id=uuid4())
    assessment = _generated_assessment(user.usr_id)
    request = _answer_request(assessment, 5)
    assessment.kas_status = state
    service, repository, db = _submission_service(assessment)

    with pytest.raises(ProblemDetailError) as raised:
        await service.submit_knowledge_assessment_answers(
            user, assessment.kas_id, request
        )

    assert raised.value.status_code == 409
    repository.complete.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_submit_rolls_back_and_sanitizes_unexpected_failure():
    user = SimpleNamespace(usr_id=uuid4())
    assessment = _generated_assessment(user.usr_id)
    service, repository, db = _submission_service(assessment)
    repository.complete.side_effect = RuntimeError("database secret")

    with pytest.raises(ProblemDetailError) as raised:
        await service.submit_knowledge_assessment_answers(
            user,
            assessment.kas_id,
            _answer_request(assessment, 5),
        )

    assert raised.value.status_code == 500
    assert "secret" not in raised.value.detail
    db.rollback.assert_awaited_once()


def _assessment_in_state(user_id, state):
    assessment = _generated_assessment(user_id)
    assessment.kas_status = state
    now = datetime.now(UTC).replace(tzinfo=None)
    if state in {
        KnowledgeAssessmentStatusEnum.PENDING,
        KnowledgeAssessmentStatusEnum.FAILED,
        KnowledgeAssessmentStatusEnum.SKIPPED,
    }:
        assessment.questions = []
    if state is KnowledgeAssessmentStatusEnum.FAILED:
        assessment.kas_error_code = "generation_failed"
    elif state is KnowledgeAssessmentStatusEnum.SKIPPED:
        assessment.kas_skip = True
        assessment.kas_level = StepLevelEnum.BEGINNER
        assessment.kas_completed_at = now
    elif state is KnowledgeAssessmentStatusEnum.COMPLETED:
        assessment.kas_score = 4
        assessment.kas_level = StepLevelEnum.ADVANCED
        assessment.kas_completed_at = now
    return assessment


@pytest.mark.anyio
@pytest.mark.parametrize(
    "state,question_count",
    [
        (KnowledgeAssessmentStatusEnum.PENDING, 0),
        (KnowledgeAssessmentStatusEnum.GENERATED, 5),
        (KnowledgeAssessmentStatusEnum.SKIPPED, 0),
        (KnowledgeAssessmentStatusEnum.COMPLETED, 5),
        (KnowledgeAssessmentStatusEnum.FAILED, 0),
    ],
)
async def test_get_projects_all_states_without_private_answer_key(
    state, question_count
):
    user = SimpleNamespace(usr_id=uuid4())
    assessment = _assessment_in_state(user.usr_id, state)
    repository = MagicMock()
    repository.get_accessible = AsyncMock(return_value=assessment)
    service = KnowledgeAssessmentService(
        repository=repository,
        db=MagicMock(),
    )

    result = await service.get_knowledge_assessment(
        user, assessment.kas_id
    )

    assert result.status is state
    assert len(result.questions) == question_count
    serialized = str(result.model_dump(mode="json"))
    assert "is_correct" not in serialized
    assert "correct_alternative_id" not in serialized


@pytest.mark.anyio
async def test_get_conceals_missing_and_unowned_with_same_not_found():
    repository = MagicMock()
    repository.get_accessible = AsyncMock(return_value=None)
    service = KnowledgeAssessmentService(
        repository=repository,
        db=MagicMock(),
    )
    user = SimpleNamespace(usr_id=uuid4())

    with pytest.raises(ProblemDetailError) as first:
        await service.get_knowledge_assessment(user, uuid4())
    with pytest.raises(ProblemDetailError) as second:
        await service.get_knowledge_assessment(user, uuid4())

    assert first.value.status_code == second.value.status_code == 404
    assert first.value.detail == second.value.detail
