import json
from importlib import import_module
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from sidebrain_back.tasks.prepare_next_step_content_task import (
    GeneratedContent,
    GeneratedLesson,
    StepContentGenerator,
)

step_task_module = import_module(
    "sidebrain_back.tasks.prepare_next_step_content_task"
)


def _lesson_text(length=1400):
    prefix = "## Conceito\n\n"
    return prefix + "x" * (length - len(prefix))


def _quizzes():
    return [
        {"question": f"**Pergunta {index}:** explique o conceito?"}
        for index in range(1, 6)
    ]


def _missions(count=3):
    return [
        {
            "title": "Pratique",
            "difficulty": "medium",
            "xp_reward": 0,
            "criteria": "number_of_lessons_completed",
            "criteria_value": 3,
        }
        for _ in range(count)
    ]


def test_step_task_disposes_async_engine_after_execution(monkeypatch):
    disposed = []
    step_id = uuid4()

    async def prepare(received_step_id):
        assert received_step_id == step_id
        return {"status": "generated", "step_id": str(step_id)}

    async def dispose():
        disposed.append(True)

    monkeypatch.setattr(step_task_module, "_prepare_step_content", prepare)
    monkeypatch.setattr(
        step_task_module, "engine", SimpleNamespace(dispose=dispose)
    )

    result = step_task_module.prepare_next_step_content_task.run(str(step_id))

    assert result == {"status": "generated", "step_id": str(step_id)}
    assert disposed == [True]


def test_step_task_disposes_async_engine_after_failure(monkeypatch):
    disposed = []

    async def fail(_step_id):
        raise RuntimeError("database unavailable")

    async def dispose():
        disposed.append(True)

    monkeypatch.setattr(step_task_module, "_prepare_step_content", fail)
    monkeypatch.setattr(
        step_task_module, "engine", SimpleNamespace(dispose=dispose)
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        step_task_module.prepare_next_step_content_task.run(str(uuid4()))

    assert disposed == [True]


def test_generated_content_accepts_domain_fields_only():
    content = GeneratedContent.model_validate(
        {
            "lessons": [
                {
                    "title": f"Lição {position}",
                    "text": _lesson_text(),
                    "quizzes": _quizzes(),
                }
                for position in range(1, 4)
            ],
            "missions": _missions(),
        }
    )

    assert len(content.lessons) == 3
    assert len(content.lessons[0].quizzes) == 5
    assert content.lessons[0].quizzes[0].question.startswith("**Pergunta")
    assert content.missions[0].xp_reward == 0


@pytest.mark.parametrize("length", [999, 2001])
def test_incremental_lesson_enforces_text_length_bounds(length):
    with pytest.raises(ValidationError):
        GeneratedLesson(
            title="Lição", text=_lesson_text(length), quizzes=_quizzes()
        )


@pytest.mark.parametrize("length", [1000, 2000])
def test_incremental_lesson_accepts_text_length_boundaries(length):
    lesson = GeneratedLesson(
        title="Lição", text=_lesson_text(length), quizzes=_quizzes()
    )

    assert len(lesson.text) == length


def test_incremental_prompt_matches_persisted_open_answer_quiz_schema():
    class FakeCompletions:
        def __init__(self):
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=json.dumps({"lessons": [], "missions": []})
                        )
                    )
                ]
            )

    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    StepContentGenerator(client).generate({"constraints": []})

    assert "temperature" not in completions.kwargs
    assert completions.kwargs["timeout"] == 120
    system_prompt = completions.kwargs["messages"][0]["content"]
    assert "entre 1000 e 1700 caracteres" in system_prompt
    assert "nunca ultrapasse 1700" in system_prompt
    assert "somente question" in system_prompt
    assert "sem options, alternatives, answer ou gabarito" in system_prompt
    assert "Não inclua um wrapper step" in system_prompt


def test_generated_content_rejects_unpersisted_multiple_choice_fields():
    payload = {
        "lessons": [
            {
                "title": f"Lição {position}",
                "text": _lesson_text(),
                "quizzes": [
                    {
                        "question": "**Pergunta:** qual é a resposta?",
                        "options": ["A", "B"],
                        "answer": "A",
                    }
                ],
            }
            for position in range(1, 4)
        ],
        "missions": _missions(),
    }

    with pytest.raises(ValidationError):
        GeneratedContent.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {
            "lessons": [
                {
                    "title": "Só uma",
                    "text": _lesson_text(),
                    "quizzes": _quizzes(),
                }
            ]
            * 3,
            "missions": [],
        },
        {
            "lessons": [
                {
                    "title": "Lição",
                    "text": _lesson_text(),
                    "quizzes": _quizzes(),
                }
            ]
            * 3,
            "missions": [
                {
                    "title": "Conclua 3 lições",
                    "difficulty": "easy",
                    "xp_reward": 10,
                    "criteria": "complete_a_step",
                    "criteria_value": 0,
                }
            ],
        },
    ],
)
def test_generated_content_requires_missions_and_valid_criteria(payload):
    with pytest.raises(ValidationError):
        GeneratedContent.model_validate(payload)


def test_generated_content_rejects_persistence_control_fields():
    with pytest.raises(ValidationError):
        GeneratedContent.model_validate(
            {
                "lessons": [
                    {
                        "title": "Variáveis",
                        "text": _lesson_text(),
                        "quizzes": _quizzes(),
                    },
                    {
                        "title": "Tipos",
                        "text": _lesson_text(),
                        "quizzes": _quizzes(),
                    },
                    {
                        "title": "Operadores",
                        "text": _lesson_text(),
                        "quizzes": _quizzes(),
                        "lsn_id": "forbidden",
                    },
                ],
                "missions": _missions(),
            }
        )
