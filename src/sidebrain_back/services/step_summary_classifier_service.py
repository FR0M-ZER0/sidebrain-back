import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CORPUS_PATH = _DATA_DIR / "step_summary_corpus.json"
_STOPWORDS_PATH = _DATA_DIR / "step_summary_stopwords.json"

SINONIMOS = {
    "assíncrono": "async",
    "assíncrona": "async",
    "assíncronos": "async",
    "assíncronas": "async",
    "promessa": "promise",
    "promessas": "promise",
    "exceção": "erro",
    "exceções": "erro",
    "matriz": "array",
    "vetor": "array",
}

_REGEX_SINONIMOS = re.compile(
    r"\b("
    + "|".join(sorted(map(re.escape, SINONIMOS), key=len, reverse=True))
    + r")\b"
)


def preprocessar(texto: str) -> str:
    texto = texto.replace("`", " ").lower()
    return _REGEX_SINONIMOS.sub(lambda match: SINONIMOS[match.group(0)], texto)


@lru_cache(maxsize=1)
def _load_model() -> Pipeline:
    with _CORPUS_PATH.open(encoding="utf-8") as file:
        records = json.load(file)
    if not isinstance(records, list) or not records:
        raise ValueError("O corpus de treinamento não pode estar vazio.")
    if any(
        not isinstance(record, dict)
        or not isinstance(record.get("text"), str)
        or not record["text"].strip()
        or not isinstance(record.get("subject"), str)
        or not record["subject"].strip()
        for record in records
    ):
        raise ValueError("O corpus de treinamento contém registros inválidos.")
    with _STOPWORDS_PATH.open(encoding="utf-8") as file:
        stopwords = json.load(file)
    model = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    preprocessor=preprocessar,
                    token_pattern=r"(?u)\b[a-zA-ZÀ-ÿ_][\wÀ-ÿ]+\b",
                    ngram_range=(1, 1),
                    stop_words=stopwords,
                    strip_accents="unicode",
                    sublinear_tf=True,
                    min_df=1,
                ),
            ),
            (
                "clf",
                LinearSVC(C=1, class_weight="balanced", random_state=42),
            ),
        ]
    )
    model.fit(
        [record["text"] for record in records],
        [record["subject"] for record in records],
    )
    return model


class StepSummaryClassifierService:
    def __init__(self, model: Any | None = None) -> None:
        self.model = model

    def classify_topics(self, texts: list[str]) -> list[str]:
        if not texts:
            return []

        model = self.model if self.model is not None else _load_model()
        return [str(topic) for topic in model.predict(texts)]


def get_step_summary_classifier_service() -> StepSummaryClassifierService:
    return StepSummaryClassifierService()
