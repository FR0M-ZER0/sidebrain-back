import importlib
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from sidebrain_back.enums.mission_criteria_enum import MissionCriteriaEnum
from sidebrain_back.schemas.generation_schema import (
    GeneratedTrack,
    GenerationInput,
)
from sidebrain_back.schemas.rag_schema import RagReferenceSchema
from sidebrain_back.services.generation_errors import GenerationValidationError
from sidebrain_back.services.generation_service import GenerationService
from sidebrain_back.services.mission_generation_service import (
    MissionGenerationService,
)

generation_service_module = importlib.import_module(
    "sidebrain_back.services.generation_service"
)


def _generated_track(lesson_count: int, mission: dict | None) -> dict:
    return {
        "icon": "📘",
        "title": "Python",
        "description": "Fundamentos",
        "steps": [
            {
                "position": 1,
                "level": "beginner",
                "title": "Fundamentos",
                "lessons": [
                    {
                        "position": position,
                        "title": f"Lição {position}",
                        "text": "Conteúdo da lição. " * 30,
                        "quiz": {"question": f"Pergunta {position}?"},
                    }
                    for position in range(1, lesson_count + 1)
                ],
                "mission": mission,
            }
        ],
    }


def _mission() -> dict:
    return {
        "title": "Pratique Python",
        "difficulty": "easy",
        "xp_reward": 10,
        "criteria": "number_of_lessons_completed",
        "criteria_value": 3,
    }


@pytest.mark.parametrize(
    ("criteria", "criteria_value", "expected_title"),
    [
        (
            "number_of_lessons_completed",
            3,
            "Conclua 3 lições da etapa: Fundamentos de JavaScript",
        ),
        (
            "number_of_lessons_completed",
            1,
            "Conclua 1 lição da etapa: Fundamentos de JavaScript",
        ),
        (
            "get_all_answer_right_in_a_lesson",
            1,
            "Acerte todas as respostas de uma lição: "
            "Fundamentos de JavaScript",
        ),
        ("complete_a_step", 1, "Conclua a etapa: Fundamentos de JavaScript"),
        ("complete_a_track", 1, "Conclua a trilha: Python"),
        (
            "number_of_steps_completed",
            2,
            "Conclua 2 etapas da trilha: Python",
        ),
        (
            "get_all_answers_right",
            1,
            "Acerte todas as respostas dos quizzes: Fundamentos de JavaScript",
        ),
    ],
)
def test_mission_titles_are_derived_from_measurable_criteria(
    criteria, criteria_value, expected_title
):
    title = MissionGenerationService.build_measurable_title(
        MissionCriteriaEnum(criteria),
        criteria_value,
        step_title="Fundamentos de JavaScript",
        track_title="Python",
    )

    assert title == expected_title


def test_initial_track_mission_title_is_aligned_before_persistence():
    generated = GeneratedTrack.model_validate(
        _generated_track(lesson_count=3, mission=_mission())
    )
    generated.steps[0].mission.title = "Construir um servidor RESTful"

    MissionGenerationService.align_track_mission_titles(generated)

    assert generated.steps[0].mission.title == (
        "Conclua 3 lições da etapa: Fundamentos"
    )


def test_measurable_mission_title_respects_database_length_limit():
    title = MissionGenerationService.build_measurable_title(
        criteria=MissionCriteriaEnum.COMPLETE_A_STEP,
        criteria_value=1,
        step_title="Etapa " + "x" * 300,
    )

    assert len(title) == MissionGenerationService.MAX_TITLE_LENGTH


class FakeCompletions:
    def __init__(self, contents: list[str]):
        self.contents = iter(contents)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = next(self.contents)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                )
            ]
        )


def _payload() -> GenerationInput:
    return GenerationInput(
        request_id=uuid4(),
        user_id=uuid4(),
        goal="Aprender Python",
        topic="Python",
    )


def _patch_client(monkeypatch, completions: FakeCompletions) -> None:
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions),
    )
    monkeypatch.setattr(
        generation_service_module, "get_groq_client", lambda: client
    )


def test_generation_retries_once_when_ai_output_violates_track_schema(
    monkeypatch,
):
    invalid = json.dumps(_generated_track(lesson_count=2, mission=None))
    valid = json.dumps(_generated_track(lesson_count=3, mission=_mission()))
    completions = FakeCompletions([invalid, valid])
    _patch_client(monkeypatch, completions)

    generated = GenerationService(None, None).generate_with_ai(_payload())

    assert len(completions.calls) == 2
    assert len(generated.steps[0].lessons) == 3
    assert generated.steps[0].mission.title == "Pratique Python"
    retry_prompt = completions.calls[1]["messages"][0]["content"]
    assert "A resposta anterior foi rejeitada pela validação" in retry_prompt
    assert "pelo menos três lições" in retry_prompt


def test_generation_validation_failure_is_bounded_and_reports_schema_issues(
    monkeypatch,
):
    invalid = json.dumps(_generated_track(lesson_count=2, mission=None))
    completions = FakeCompletions([invalid, invalid])
    _patch_client(monkeypatch, completions)

    with pytest.raises(GenerationValidationError) as raised:
        GenerationService(None, None).generate_with_ai(_payload())

    assert len(completions.calls) == GenerationService.VALIDATION_ATTEMPTS
    assert raised.value.validation_issues


def test_generated_track_title_removes_redundant_prefix(monkeypatch):
    generated_payload = _generated_track(lesson_count=3, mission=_mission())
    generated_payload["title"] = "Trilha de Python"
    completions = FakeCompletions([json.dumps(generated_payload)])
    _patch_client(monkeypatch, completions)

    generated = GenerationService(None, None).generate_with_ai(_payload())

    assert generated.title == "Python"


def test_generated_initial_lessons_include_cited_rag_source(monkeypatch):
    generated_payload = _generated_track(lesson_count=3, mission=_mission())
    for lesson in generated_payload["steps"][0]["lessons"]:
        lesson["text"] = "[Fonte 1] " + "Conteúdo da lição. " * 50
    completions = FakeCompletions([json.dumps(generated_payload)])
    _patch_client(monkeypatch, completions)
    reference = RagReferenceSchema(
        chunk_id="a" * 64,
        text="Python lists preserve insertion order.",
        source_name="python-tutorial",
        source_url="https://docs.example/tutorial/lists",
        title="Lists",
        section_path="Tutorial > Lists",
        language="python",
        level="beginner",
        content_type="tutorial",
        topics=["lists"],
        license="PSF-2.0",
        external_processing_allowed=True,
    )

    generated = GenerationService(None, None).generate_with_ai(
        _payload(), [reference]
    )

    for lesson in generated.steps[0].lessons:
        assert "[Fonte 1]" in lesson.text
        assert "https://docs.example/tutorial/lists" in lesson.text
        assert 420 <= len(lesson.text) <= 1000
