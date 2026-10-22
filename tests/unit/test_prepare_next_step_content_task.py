import pytest
from pydantic import ValidationError

from sidebrain_back.tasks.prepare_next_step_content_task import (
    GeneratedContent,
)


def test_generated_content_accepts_domain_fields_only():
    content = GeneratedContent.model_validate(
        {
            "lessons": [
                {
                    "title": f"Lição {position}",
                    "text": "Conteúdo",
                    "quizzes": [{"question": f"Pergunta {position}?"}],
                }
                for position in range(1, 4)
            ],
            "missions": [
                {
                    "title": "Pratique",
                    "difficulty": "medium",
                    "xp_reward": 0,
                    "criteria": "number_of_lessons_completed",
                    "criteria_value": 3,
                }
            ],
        }
    )

    assert len(content.lessons) == 3
    assert content.lessons[0].quizzes[0].question == "Pergunta 1?"
    assert content.missions[0].xp_reward == 0


@pytest.mark.parametrize(
    "payload",
    [
        {
            "lessons": [{"title": "Só uma", "text": "Conteúdo", "quizzes": []}]
            * 3,
            "missions": [],
        },
        {
            "lessons": [{"title": "Lição", "text": "Conteúdo", "quizzes": []}]
            * 3,
            "missions": [
                {
                    "title": "Inválida",
                    "difficulty": "medium",
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
                        "text": "Conteúdo",
                        "quizzes": [],
                    },
                    {
                        "title": "Tipos",
                        "text": "Conteúdo",
                        "quizzes": [],
                    },
                    {
                        "title": "Operadores",
                        "text": "Conteúdo",
                        "quizzes": [],
                        "lsn_id": "forbidden",
                    },
                ],
                "missions": [
                    {
                        "title": "Pratique",
                        "difficulty": "easy",
                        "xp_reward": 10,
                        "criteria": "complete_a_step",
                        "criteria_value": 1,
                    }
                ],
            }
        )
