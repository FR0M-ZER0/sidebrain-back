import asyncio
import importlib
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.enums.step_status_enum import StepStatusEnum
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.mission_model import Mission
from sidebrain_back.schemas.rag_schema import (
    RagClassificationSchema,
    RagReferenceSchema,
)
from sidebrain_back.services.rag_generation_context_service import (
    RagGenerationContextService,
)

step_task_module = importlib.import_module(
    "sidebrain_back.tasks.prepare_next_step_content_task"
)


class FakeRouter:
    def __init__(self, decision: RagClassificationSchema):
        self.decision = decision
        self.calls: list[tuple[str, str]] = []

    def should_use_rag(self, goal: str, topic: str) -> RagClassificationSchema:
        self.calls.append((goal, topic))
        return self.decision


class FakeRetriever:
    def __init__(self):
        self.calls: list[dict] = []

    async def retrieve(self, **kwargs) -> list[RagReferenceSchema]:
        self.calls.append(kwargs)
        return []


def test_step_context_uses_original_goal_topic_and_maps_pro_to_advanced():
    router = FakeRouter(
        RagClassificationSchema(
            use_rag=True, language="javascript", confidence=0.92
        )
    )
    retriever = FakeRetriever()
    service = RagGenerationContextService(router, retriever)

    references = asyncio.run(
        service.get_references(
            goal="Aprender async/await em JavaScript",
            topic="JavaScript",
            level="pro",
        )
    )

    assert references == []
    assert router.calls == [
        ("Aprender async/await em JavaScript", "JavaScript")
    ]
    assert retriever.calls[0]["language"] == "javascript"
    assert retriever.calls[0]["level"] == "advanced"


def test_manual_track_without_original_context_does_not_classify_or_retrieve():
    router = FakeRouter(
        RagClassificationSchema(use_rag=False, language=None, confidence=0.0)
    )
    retriever = FakeRetriever()
    service = RagGenerationContextService(router, retriever)

    references = asyncio.run(
        service.get_references(goal=None, topic=None, level="beginner")
    )

    assert references == []
    assert router.calls == []
    assert retriever.calls == []


def _step_with_track():
    step = SimpleNamespace(
        stp_id=uuid4(),
        stp_title="Async",
        stp_level=StepLevelEnum.PRO,
        stp_status=StepStatusEnum.IDLE,
        stp_updated_at=datetime.now(UTC).replace(tzinfo=None),
        lessons=[],
        missions=[],
        track=None,
    )
    step.track = SimpleNamespace(
        trk_id=uuid4(),
        trk_title="JavaScript",
        trk_description="Async programming",
        steps=[step],
    )
    return step


class FakeDbSession:
    def __init__(self):
        self.added = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None


class FakeStepRepository:
    def __init__(self, step):
        self.step = step

    async def get_step_for_generation(self, _step_id):
        return self.step

    async def has_active_generated_content(self, _step_id):
        return False


class FakeStepGenerator:
    def __init__(self):
        self.contexts = []

    def generate(self, context):
        self.contexts.append(context)
        return {
            "lessons": [
                {
                    "title": f"Async {position}",
                    "text": (
                        "## Conceito\n\n" + ("Conteúdo. " * 120) + " [Fonte 1]"
                    ),
                    "quizzes": [
                        {"question": f"**Pergunta {index}:** explique?"}
                        for index in range(1, 6)
                    ],
                }
                for position in range(1, 4)
            ],
            "missions": [
                {
                    "title": "Pratique async",
                    "difficulty": "medium",
                    "xp_reward": 20,
                    "criteria": "complete_a_step",
                    "criteria_value": 1,
                }
            ]
            + [
                {
                    "title": "Pratique async",
                    "difficulty": "medium",
                    "xp_reward": 20,
                    "criteria": "number_of_lessons_completed",
                    "criteria_value": 3,
                }
                for _ in range(2)
            ],
        }


class FakeStepRagContext:
    def __init__(self):
        self.calls = []
        self.reference = RagReferenceSchema(
            chunk_id="b" * 64,
            text="Promises represent an eventual result.",
            source_name="mdn-javascript",
            source_url=(
                "https://developer.mozilla.org/en-US/docs/Web/JavaScript/"
                "Reference/Global_Objects/Promise"
            ),
            title="Promise",
            section_path="JavaScript > Promise",
            language="javascript",
            level="advanced",
            content_type="reference",
            topics=["promise", "async"],
            license="CC-BY-SA-2.5-or-later",
            external_processing_allowed=True,
        )

    async def get_references(self, **kwargs):
        self.calls.append(kwargs)
        return [self.reference]


def test_step_task_uses_persisted_goal_topic_before_locked_generation(
    monkeypatch,
):
    step = _step_with_track()
    db_session = FakeDbSession()
    generation_request = SimpleNamespace(
        goal="Aprender async/await em JavaScript",
        topic="JavaScript",
    )
    request_lookup = []

    class FakeGenerationRequestRepository:
        def __init__(self, _db):
            pass

        async def get_rag_context_by_step_id(self, step_id):
            request_lookup.append(step_id)
            return generation_request, StepLevelEnum.PRO

    monkeypatch.setattr(step_task_module, "async_session", lambda: db_session)
    monkeypatch.setattr(
        step_task_module,
        "GenerationRequestRepository",
        FakeGenerationRequestRepository,
    )
    monkeypatch.setattr(
        step_task_module,
        "TrackRepository",
        lambda _db: FakeStepRepository(step),
    )
    rag_context = FakeStepRagContext()
    generator = FakeStepGenerator()

    result = asyncio.run(
        step_task_module._prepare_step_content(
            step.stp_id,
            generator=generator,
            rag_context_service=rag_context,
        )
    )

    assert result["status"] == "generated"
    assert request_lookup == [step.stp_id]
    assert rag_context.calls == [
        {
            "goal": "Aprender async/await em JavaScript",
            "topic": "JavaScript",
            "level": "pro",
        }
    ]
    assert generator.contexts[0]["reference_context"][0]["url"] == (
        rag_context.reference.source_url
    )
    assert any(
        "projetos ou entregáveis" in constraint
        for constraint in generator.contexts[0]["constraints"]
    )
    missions = [item for item in db_session.added if isinstance(item, Mission)]
    assert len(missions) == 3
    assert missions[0].msn_title == "Conclua a etapa: Async"
    lessons = [item for item in db_session.added if isinstance(item, Lesson)]
    assert len(lessons) == 3
    assert all(
        rag_context.reference.source_url in item.lsn_text for item in lessons
    )
    assert all(1000 <= len(item.lsn_text) <= 2000 for item in lessons)
    assert all(item.lsn_text.startswith("## Conceito") for item in lessons)
    quizzes = [
        item for item in db_session.added if item.__class__.__name__ == "Quiz"
    ]
    assert len(quizzes) == 15


def test_manual_step_does_not_invoke_rag_context_service(monkeypatch):
    step = _step_with_track()

    class FakeGenerationRequestRepository:
        def __init__(self, _db):
            pass

        async def get_rag_context_by_step_id(self, _step_id):
            return None

    monkeypatch.setattr(
        step_task_module, "async_session", lambda: FakeDbSession()
    )
    monkeypatch.setattr(
        step_task_module,
        "GenerationRequestRepository",
        FakeGenerationRequestRepository,
    )
    monkeypatch.setattr(
        step_task_module,
        "TrackRepository",
        lambda _db: FakeStepRepository(step),
    )
    rag_context = FakeStepRagContext()
    generator = FakeStepGenerator()

    result = asyncio.run(
        step_task_module._prepare_step_content(
            step.stp_id,
            generator=generator,
            rag_context_service=rag_context,
        )
    )

    assert result["status"] == "generated"
    assert rag_context.calls == []
    assert "reference_context" not in generator.contexts[0]
