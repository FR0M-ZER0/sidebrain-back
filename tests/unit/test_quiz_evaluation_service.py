import json
from types import SimpleNamespace

import pytest

from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.services import quiz_evaluation_service
from sidebrain_back.services.quiz_evaluation_service import (
    QuizEvaluationService,
)


class FakeCompletions:
    def __init__(self, content):
        self.content = content
        self.call = None

    def create(self, **kwargs):
        self.call = kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=self.content))
            ]
        )


@pytest.mark.parametrize("rate", list(AnswerRateEnum))
def test_evaluator_returns_rate_selected_by_ai(monkeypatch, rate):
    completions = FakeCompletions(json.dumps({"rate": rate.value}))
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr(
        quiz_evaluation_service, "get_groq_client", lambda: client
    )

    result = QuizEvaluationService().evaluate("What is 2 + 2?", "4")

    assert result is rate
    assert "What is 2 + 2?" in completions.call["messages"][0]["content"]
    assert "4" in completions.call["messages"][0]["content"]
    assert completions.call["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize("content", [None, "not json", '{"rate":"unknown"}'])
def test_evaluator_rejects_missing_or_invalid_ai_rate(monkeypatch, content):
    completions = FakeCompletions(content)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr(
        quiz_evaluation_service, "get_groq_client", lambda: client
    )

    with pytest.raises(ValueError):
        QuizEvaluationService().evaluate("Question", "Answer")
