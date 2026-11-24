import json

import pytest
from sklearn.svm import LinearSVC

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


def test_model_uses_linear_svc_and_expected_labels():
    model = _load_model()
    assert isinstance(model.named_steps["clf"], LinearSVC)
    assert set(model.classes_) == {
        "arrays",
        "async",
        "classes",
        "condicionais",
        "dom",
        "funcoes",
        "html",
        "nodejs",
        "objetos",
        "strings",
        "testes",
        "tratamento_erros",
        "variaveis",
    }
    assert _load_model() is model


@pytest.mark.parametrize("records", [[], [{"text": "", "subject": "html"}]])
def test_invalid_corpus_is_rejected(tmp_path, monkeypatch, records):
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    monkeypatch.setattr(
        "sidebrain_back.services.step_summary_classifier_service._CORPUS_PATH",
        path,
    )
    with pytest.raises(ValueError, match="corpus"):
        _load_model()


def test_empty_batch_does_not_load_model():
    classifier = StepSummaryClassifierService()

    assert classifier.classify_topics([]) == []
