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
                        "text": "## Conceito\n\n" + "Conteúdo da lição. " * 80,
                        "quizzes": [
                            {
                                "question": (
                                    f"**Pergunta {quiz_index}:** "
                                    f"explique o conceito {position}?"
                                )
                            }
                            for quiz_index in range(1, 6)
                        ],
                    }
                    for position in range(1, lesson_count + 1)
                ],
                "missions": [mission] * 3 if mission is not None else [],
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
    generated.steps[0].missions[0].title = "Construir um servidor RESTful"

    MissionGenerationService.align_track_mission_titles(generated)

    assert generated.steps[0].missions[0].title == (
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
        generation_service_module, "get_openai_client", lambda: client
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
    assert len(generated.steps[0].missions) == 3
    assert generated.steps[0].missions[0].title == "Pratique Python"
    retry_prompt = completions.calls[1]["messages"][0]["content"]
    assert "A resposta anterior foi rejeitada pela validação" in retry_prompt
    assert "pelo menos três lições" in retry_prompt


def test_generation_retry_explains_quiz_markdown_belongs_in_value(monkeypatch):
    invalid_payload = _generated_track(lesson_count=3, mission=_mission())
    invalid_quiz = invalid_payload["steps"][0]["lessons"][1]["quizzes"][2]
    del invalid_quiz["question"]
    invalid_quiz[
        "question:**Pergunta:** Como um dicionário associa informações?"
    ] = "Como um dicionário associa informações?"
    valid_payload = _generated_track(lesson_count=3, mission=_mission())
    completions = FakeCompletions(
        [json.dumps(invalid_payload), json.dumps(valid_payload)]
    )
    _patch_client(monkeypatch, completions)

    GenerationService(None, None).generate_with_ai(_payload())

    retry_prompt = completions.calls[1]["messages"][0]["content"]
    assert "chave literal `question`" in retry_prompt
    assert "Markdown pertence ao valor da pergunta" in retry_prompt
    assert "nunca ao nome da chave" in retry_prompt


def test_generation_retry_limits_lesson_length_with_safety_margin(monkeypatch):
    invalid_payload = _generated_track(lesson_count=3, mission=_mission())
    invalid_payload["steps"][0]["lessons"][2]["text"] = (
        "## Conceito\n\n" + "x" * 2000
    )
    valid_payload = _generated_track(lesson_count=3, mission=_mission())
    completions = FakeCompletions(
        [json.dumps(invalid_payload), json.dumps(valid_payload)]
    )
    _patch_client(monkeypatch, completions)

    GenerationService(None, None).generate_with_ai(_payload())

    retry_prompt = completions.calls[1]["messages"][0]["content"]
    assert "1000 e 1700 caracteres" in retry_prompt
    assert "aproximadamente 1500" in retry_prompt
    assert "string_too_long" in retry_prompt


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
        lesson["text"] = (
            "## Conceito\n\n[Fonte 1] " + "Conteúdo da lição. " * 80
        )
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
        assert 1000 <= len(lesson.text) <= 2000
