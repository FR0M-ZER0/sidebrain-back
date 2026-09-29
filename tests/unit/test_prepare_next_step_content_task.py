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
                    "title": "Variáveis",
                    "text": "Conteúdo",
                    "quizzes": [{"question": "O que é uma variável?"}],
                }
            ],
            "missions": [],
        }
    )

    assert content.lessons[0].quizzes[0].question == "O que é uma variável?"


def test_generated_content_rejects_persistence_control_fields():
    with pytest.raises(ValidationError):
        GeneratedContent.model_validate(
            {
                "lessons": [
                    {
                        "title": "Variáveis",
                        "text": "Conteúdo",
                        "lsn_id": "forbidden",
                    }
                ]
            }
        )
