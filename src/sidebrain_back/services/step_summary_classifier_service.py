import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from sidebrain_back.core.constants import Env

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


@lru_cache(maxsize=2)
def _load_model(model_path: str) -> Any:
    path = Path(model_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path

    if not path.is_file():
        raise FileNotFoundError(
            f"Artefato do classificador não encontrado: {path}"
        )

    for module_name in ("__main__", "__mp_main__"):
        main_module = sys.modules.get(module_name)
        if main_module is not None:
            main_module.preprocessar = preprocessar
    return joblib.load(path)


class StepSummaryClassifierService:
    def __init__(self, model: Any | None = None) -> None:
        self.model = model

    def classify_topics(self, texts: list[str]) -> list[str]:
        if not texts:
            return []

        model = (
            self.model
            if self.model is not None
            else _load_model(str(Env.STEP_SUMMARY_MODEL_PATH))
        )
        return [str(topic) for topic in model.predict(texts)]


def get_step_summary_classifier_service() -> StepSummaryClassifierService:
    return StepSummaryClassifierService()
