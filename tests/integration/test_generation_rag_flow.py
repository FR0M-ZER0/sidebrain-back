from __future__ import annotations

import importlib
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.enums.generation_status_enum import GenerationStatusEnum
from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.enums.step_status_enum import StepStatusEnum
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.mission_model import Mission
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.track_model import Track
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.generation_request_repository import (
    GenerationRequestRepository,
)
from sidebrain_back.schemas.generation_schema import (
    GeneratedTrack,
    GenerationInput,
    GenerationSuccess,
)
from sidebrain_back.schemas.rag_schema import (
    RagClassificationSchema,
    RagReferenceSchema,
)
from sidebrain_back.services.generation_service import GenerationService
from sidebrain_back.services.rag_generation_context_service import (
    RagGenerationContextService,
)
from sidebrain_back.services.rag_routing_service import RagRoutingService
from sidebrain_back.tasks.prepare_next_step_content_task import (
    _prepare_step_content,
)

generation_task_module = importlib.import_module(
    "sidebrain_back.tasks.generate_track_task"
)
step_task_module = importlib.import_module(
    "sidebrain_back.tasks.prepare_next_step_content_task"
)


class FakeRagRouter:
    def __init__(
        self,
        use_rag: bool,
        language: str | None,
        error: Exception | None = None,
    ):
        self.use_rag = use_rag
        self.language = language
        self.error = error
        self.calls = []

    def should_use_rag(self, goal: str, topic: str):
        self.calls.append((goal, topic))
        if self.error is not None:
            raise self.error
        return RagClassificationSchema(
            use_rag=self.use_rag,
            language=self.language if self.use_rag else None,
            confidence=0.95 if self.use_rag else 0.0,
        )


class FakeRagRetriever:
    def __init__(self, references=None, error: Exception | None = None):
        self.references = references or []
        self.error = error
        self.calls = []

    async def retrieve(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.references


class FakeGroqCompletions:
    def __init__(self):
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        raise AssertionError("unrelated context must not call Groq classifier")


class SharedSessionContext:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_args):
        return None


class FakeStepGenerator:
    def __init__(self, contexts=None):
        self.contexts = contexts if contexts is not None else []

    def generate(self, context):
        self.contexts.append(context)
        return {
            "lessons": [
                {
                    "title": f"Promises {position}",
                    "text": "Conteúdo de teste",
                    "quizzes": [
                        {"question": f"O que é uma Promise? ({position})"}
                    ],
                }
                for position in range(1, 4)
            ],
            "missions": [
                {
                    "title": "Implemente uma Promise",
                    "difficulty": "medium",
                    "xp_reward": 50,
                    "criteria": "number_of_lessons_completed",
                    "criteria_value": 3,
                }
            ],
        }


def _reference(language="python"):
    is_javascript = language == "javascript"
    source_name = "mdn-javascript" if is_javascript else "python-tutorial"
    source_url = (
        "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/"
        "Global_Objects/Promise"
        if is_javascript
        else "https://docs.example/tutorial/lists"
    )
    return RagReferenceSchema(
        chunk_id="c" * 64,
        text=(
            "A Promise represents an eventual result."
            if is_javascript
            else "A list preserves insertion order."
        ),
        source_name=source_name,
        source_url=source_url,
        title="Promise" if is_javascript else "Lists",
        section_path=(
            "JavaScript > Promise" if is_javascript else "Tutorial > Lists"
        ),
        language=language,
        level="beginner",
        content_type="reference" if is_javascript else "tutorial",
        topics=["promise"] if is_javascript else ["lists"],
        license="CC-BY-SA-2.5-or-later" if is_javascript else "PSF-2.0",
        license_url=(
            "https://creativecommons.org/licenses/by-sa/2.5/"
            if is_javascript
            else "https://docs.python.org/3/license.html"
        ),
        external_processing_allowed=True,
    )


def _generated_track() -> GeneratedTrack:
    return GeneratedTrack.model_validate(
        {
            "icon": "📘",
            "title": "Fundamentos",
            "description": "Trilha de teste",
            "steps": [
                {
                    "position": 1,
                    "level": "beginner",
                    "title": "Primeiros passos",
                    "lessons": [
                        {
                            "position": position,
                            "title": f"Listas {position}",
                            "text": "Conteúdo válido",
                            "quiz": {
                                "question": f"O que é uma lista? ({position})"
                            },
                        }
                        for position in range(1, 4)
                    ],
                    "mission": {
                        "title": "Pratique listas",
                        "difficulty": "easy",
                        "xp_reward": 25,
                        "criteria": "number_of_lessons_completed",
                        "criteria_value": 3,
                    },
                }
            ],
        }
    )


async def _create_request(
    db: AsyncSession,
    goal: str,
    topic: str,
    *,
    with_step: bool = False,
) -> tuple[UUID, UUID, UUID | None]:
    user_id = uuid4()
    request_id = uuid4()
    step_id = uuid4() if with_step else None
    track_id = uuid4() if with_step else None
    db.add(
        User(
            usr_id=user_id,
            usr_email=f"{user_id}@example.com",
            usr_name="RAG Integration Test",
            usr_password_hash="test-hash",
            usr_is_deleted=False,
        )
    )
    await db.flush()
    if with_step:
        db.add(
            Track(
                trk_id=track_id,
                trk_user_id=user_id,
                trk_title=topic,
                trk_description="Contexto da trilha",
                trk_generation_request_id=request_id,
                trk_is_deleted=False,
            )
        )
        await db.flush()
        db.add(
            Step(
                stp_id=step_id,
                stp_track_id=track_id,
                stp_level=StepLevelEnum.PRO,
                stp_title="Async",
                stp_status=StepStatusEnum.IDLE,
                stp_is_deleted=False,
            )
        )
        await db.flush()

    request = await GenerationRequestRepository(db).create_pending(
        request_id=request_id,
        user_id=user_id,
        context_fingerprint=uuid4().hex * 2,
        goal=goal,
        topic=topic,
        knowledge_level=StepLevelEnum.BEGINNER,
        assessment_answers=None,
    )
    if track_id is not None:
        request.track_id = track_id
        request.status = GenerationStatusEnum.SUCCEEDED
    await db.commit()
    return user_id, request_id, step_id


@pytest.mark.anyio
async def test_initial_generation_uses_references_and_preserves_idempotency(
    db_session: AsyncSession,
    monkeypatch,
):
    goal = "Aprender programação em Python"
    topic = "Python"
    user_id, request_id, _step_id = await _create_request(
        db_session, goal, topic
    )
    payload = GenerationInput(
        request_id=request_id,
        user_id=user_id,
        goal=goal,
        topic=topic,
        knowledge_level=StepLevelEnum.BEGINNER,
    )
    retriever = FakeRagRetriever([_reference()])
    rag_context = RagGenerationContextService(
        FakeRagRouter(True, "python"), retriever
    )
    prompts = []
    monkeypatch.setattr(
        generation_task_module,
        "async_session",
        lambda: SharedSessionContext(db_session),
    )

    def fake_generate_with_ai(
        _service, received_payload, reference_context=None
    ):
        prompts.append(
            GenerationService.build_prompt(received_payload, reference_context)
        )
        return _generated_track()

    monkeypatch.setattr(
        GenerationService, "generate_with_ai", fake_generate_with_ai
    )

    result = await generation_task_module._run_generation(
        payload, rag_context_service=rag_context
    )
    assert result["status"] == "succeeded"
    GenerationSuccess.model_validate(result)
    assert len(prompts) == 1
    assert "https://docs.example/tutorial/lists" in prompts[0]
    assert len(retriever.calls) == 1

    repeated = await generation_task_module._run_generation(
        payload, rag_context_service=rag_context
    )
    assert repeated == result
    assert len(prompts) == 1
    assert len(retriever.calls) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("failure_stage", ["classification", "retrieval"])
async def test_rag_failure_does_not_change_generation_or_idempotency(
    db_session: AsyncSession,
    monkeypatch,
    failure_stage: str,
):
    goal = "Aprender programação em Python"
    topic = "Python"
    user_id, request_id, _step_id = await _create_request(
        db_session, goal, topic
    )
    payload = GenerationInput(
        request_id=request_id,
        user_id=user_id,
        goal=goal,
        topic=topic,
        knowledge_level=StepLevelEnum.BEGINNER,
    )
    router = FakeRagRouter(
        True,
        "python",
        error=(
            RuntimeError("classifier unavailable")
            if failure_stage == "classification"
            else None
        ),
    )
    retriever = FakeRagRetriever(
        error=(
            RuntimeError("retrieval unavailable")
            if failure_stage == "retrieval"
            else None
        ),
    )
    rag_context = RagGenerationContextService(router, retriever)
    prompts = []
    monkeypatch.setattr(
        generation_task_module,
        "async_session",
        lambda: SharedSessionContext(db_session),
    )

    def fake_generate_with_ai(
        _service, received_payload, reference_context=None
    ):
        prompts.append(
            GenerationService.build_prompt(received_payload, reference_context)
        )
        return _generated_track()

    monkeypatch.setattr(
        GenerationService, "generate_with_ai", fake_generate_with_ai
    )

    result = await generation_task_module._run_generation(
        payload, rag_context_service=rag_context
    )

    success = GenerationSuccess.model_validate(result)
    assert success.request_id == request_id
    assert result["status"] == "succeeded"
    assert len(prompts) == 1
    assert "Material de referência não confiável" not in prompts[0]
    assert router.calls == [(goal, topic)]
    assert len(retriever.calls) == (1 if failure_stage == "retrieval" else 0)
    persisted_request = await GenerationRequestRepository(db_session).get(
        request_id
    )
    assert persisted_request.status == GenerationStatusEnum.SUCCEEDED
    assert persisted_request.track_id == success.track_id

    repeated = await generation_task_module._run_generation(
        payload, rag_context_service=rag_context
    )

    assert repeated == result
    assert len(prompts) == 1
    assert router.calls == [(goal, topic)]
    assert len(retriever.calls) == (1 if failure_stage == "retrieval" else 0)


@pytest.mark.anyio
async def test_non_programming_initial_goal_generates_without_rag(
    db_session: AsyncSession,
    monkeypatch,
):
    goal = "Aprender inglês para viagens"
    topic = "Inglês"
    user_id, request_id, _step_id = await _create_request(
        db_session, goal, topic
    )
    payload = GenerationInput(
        request_id=request_id,
        user_id=user_id,
        goal=goal,
        topic=topic,
        knowledge_level=StepLevelEnum.BEGINNER,
    )
    groq_completions = FakeGroqCompletions()
    retriever = FakeRagRetriever([_reference()])
    rag_context = RagGenerationContextService(
        RagRoutingService(
            client=SimpleNamespace(
                chat=SimpleNamespace(completions=groq_completions)
            )
        ),
        retriever,
    )
    prompts = []
    monkeypatch.setattr(
        generation_task_module,
        "async_session",
        lambda: SharedSessionContext(db_session),
    )

    def fake_generate_with_ai(
        _service, received_payload, reference_context=None
    ):
        prompts.append(
            GenerationService.build_prompt(received_payload, reference_context)
        )
        return _generated_track()

    monkeypatch.setattr(
        GenerationService, "generate_with_ai", fake_generate_with_ai
    )

    result = await generation_task_module._run_generation(
        payload, rag_context_service=rag_context
    )

    assert result["status"] == "succeeded"
    assert "Material de referência não confiável" not in prompts[0]
    assert groq_completions.calls == 0
    assert retriever.calls == []


@pytest.mark.anyio
async def test_incremental_generation_uses_persisted_context_and_keeps_schema(
    db_session: AsyncSession,
    monkeypatch,
):
    user_id, _request_id, step_id = await _create_request(
        db_session,
        "Aprender async/await em JavaScript",
        "JavaScript",
        with_step=True,
    )
    rag_context = RagGenerationContextService(
        FakeRagRouter(True, "javascript"),
        FakeRagRetriever([_reference("javascript")]),
    )
    contexts = []
    monkeypatch.setattr(
        step_task_module,
        "async_session",
        lambda: SharedSessionContext(db_session),
    )
    monkeypatch.setattr(
        generation_task_module,
        "async_session",
        lambda: SharedSessionContext(db_session),
    )

    result = await _prepare_step_content(
        step_id,
        generator=FakeStepGenerator(contexts),
        rag_context_service=rag_context,
    )

    assert result["status"] == "generated"
    assert contexts[0]["reference_context"][0]["source_url"] == (
        _reference("javascript").source_url
    )
    assert contexts[0]["step"]["level"] == "pro"
    lessons = list(
        (
            await db_session.scalars(
                select(Lesson).where(Lesson.lsn_step_id == step_id)
            )
        ).all()
    )
    quizzes = list(
        (
            await db_session.scalars(
                select(Quiz).where(Quiz.qui_lesson_id == lessons[0].lsn_id)
            )
        ).all()
    )
    missions = list(
        (
            await db_session.scalars(
                select(Mission).where(Mission.msn_step_id == step_id)
            )
        ).all()
    )
    assert len(lessons) == 3
    assert len(quizzes) == 1
    assert len(missions) == 1
    assert missions[0].msn_title == "Conclua 3 lições da etapa: Async"


@pytest.mark.anyio
async def test_manual_incremental_track_does_not_request_rag_context(
    db_session: AsyncSession,
    monkeypatch,
):
    user_id, _request_id, step_id = await _create_request(
        db_session,
        "Trilha criada manualmente",
        "Comunicação",
        with_step=True,
    )
    track = await db_session.scalar(
        select(Track).where(Track.trk_user_id == user_id)
    )
    track.trk_generation_request_id = None
    await db_session.commit()
    rag_context = RagGenerationContextService(
        FakeRagRouter(True, "python"),
        FakeRagRetriever([_reference()]),
    )
    contexts = []
    monkeypatch.setattr(
        step_task_module,
        "async_session",
        lambda: SharedSessionContext(db_session),
    )

    result = await _prepare_step_content(
        step_id,
        generator=FakeStepGenerator(contexts),
        rag_context_service=rag_context,
    )

    assert result["status"] == "generated"
    assert contexts
    assert "reference_context" not in contexts[0]
    assert rag_context.router.calls == []
    assert rag_context.retriever.calls == []
