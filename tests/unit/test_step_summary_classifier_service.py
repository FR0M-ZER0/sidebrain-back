import sys
from types import ModuleType

import pytest

from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.services.step_summary_classifier_service import (
    StepSummaryClassifierService,
    _load_model,
    preprocessar,
)
from sidebrain_back.services.step_summary_generator_service import (
    StepSummaryGeneratorService,
)


@pytest.fixture(autouse=True)
def clear_model_cache():
    _load_model.cache_clear()
    yield
    _load_model.cache_clear()


def test_preprocessing_matches_training_normalization():
    assert preprocessar("`ASSÍNCRONA` e exceções") == " async  e erro"


def test_checked_in_model_classifies_feedback_topics():
    classifier = StepSummaryClassifierService()
    reason = "Faltou explicar que async retorna uma Promise."

    assert classifier.classify_topics([reason]) == ["async"]
    summary = StepSummaryGeneratorService(classifier).generate_step_summary(
        [(reason, AnswerRateEnum.ALMOST_GOT_IT)]
    )
    assert "Para revisar:\n- Assincronismo" in summary


def test_model_loads_when_dev_entrypoint_uses_mp_main(monkeypatch):
    mp_main = ModuleType("__mp_main__")
    monkeypatch.setitem(sys.modules, "__mp_main__", mp_main)

    classifier = StepSummaryClassifierService()

    assert classifier.classify_topics(
        ["Faltou explicar que async retorna uma Promise."]
    ) == ["async"]
    assert mp_main.preprocessar is preprocessar


def test_empty_batch_does_not_load_model():
    classifier = StepSummaryClassifierService()

    assert classifier.classify_topics([]) == []
