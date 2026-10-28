from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sidebrain_back.rag.rag_chunker import RagChunker
from sidebrain_back.rag.rag_config import load_rag_config
from sidebrain_back.rag.rag_document_parser import RagDocumentParser
from sidebrain_back.rag.rag_tokenizer import RagTokenizer
from sidebrain_back.schemas.rag_schema import (
    RagReferenceAttributionSchema,
    RagReferenceSchema,
)
from sidebrain_back.services.rag_retrieval_service import RagRetrievalService

_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_+#.-]+")
_EVALUATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "fixtures"
    / "rag"
    / "evaluation_queries.jsonl"
)
_DOCUMENTS_PATH = _EVALUATION_PATH.parent / "evaluation_documents"


@dataclass(frozen=True)
class RagEvaluationQuestion:
    id: str
    query: str
    language: str
    level: str
    expected: list[dict[str, str]]


@dataclass(frozen=True)
class RagEvaluationReport:
    k: int
    mean_recall_at_k: float
    questions: list[dict[str, Any]]
    model_id: str | None = None
    dimensions: int | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


def load_evaluation_questions(
    path: str | Path = _EVALUATION_PATH,
) -> list[RagEvaluationQuestion]:
    questions = []
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            questions.append(RagEvaluationQuestion(**value))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError(
                f"invalid RAG evaluation question on line {line_number}"
            ) from error
    if len(questions) != 20:
        raise ValueError(
            "RAG evaluation set must contain 20 questions, "
            f"got {len(questions)}"
        )
    if len({question.id for question in questions}) != len(questions):
        raise ValueError("RAG evaluation question IDs must be unique")
    return questions


def recall_at_k(
    results: list[Any], expected: list[dict[str, str]], k: int
) -> float:
    if not expected:
        return 0.0
    top_results = results[: max(0, k)]
    hits = sum(
        1
        for target in expected
        if any(_matches_target(result, target) for result in top_results)
    )
    return hits / len(expected)


def _matches_target(result: Any, target: dict[str, str]) -> bool:
    candidates = [result, *getattr(result, "attributions", [])]
    for candidate in candidates:
        if all(
            _value(candidate, key) == value for key, value in target.items()
        ):
            return True
    return False


def _value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


class FixtureRagRetriever:
    """Deterministic, no-network retriever used only for fixture evaluation."""

    def __init__(self, documents_path: str | Path = _DOCUMENTS_PATH):
        self.documents_path = Path(documents_path)
        config = load_rag_config()
        self.tokenizer = RagTokenizer(config.defaults.chunking.encoding)
        self.chunker = RagChunker(
            tokenizer=self.tokenizer,
            target_tokens=config.defaults.chunking.target_tokens,
            overlap_ratio=config.defaults.chunking.overlap_ratio,
        )
        self.documents = self._load_documents()

    def _load_documents(self) -> list[RagReferenceSchema]:
        parser = RagDocumentParser()
        references: list[RagReferenceSchema] = []
        for path in sorted(self.documents_path.glob("*.md")):
            source_name = path.stem
            language = (
                "javascript"
                if source_name.startswith("javascript_")
                else "python"
            )
            level = next(
                (
                    value
                    for value in ("beginner", "intermediate", "advanced")
                    if f"_{value}_" in source_name
                ),
                "beginner",
            )
            parsed = parser.parse_markdown(
                path.read_text(encoding="utf-8"),
                source_url=f"fixture://{source_name}",
            )
            chunks = self.chunker.chunk_document(
                title=parsed.title,
                sections=parsed.sections,
                attribution={
                    "source_name": source_name,
                    "source_url": f"fixture://{source_name}",
                    "title": parsed.title,
                    "language": language,
                    "level": level,
                    "content_type": "concept",
                    "topics": [],
                    "license": "fixture-local",
                    "license_url": None,
                    "external_processing_allowed": True,
                },
            )
            for chunk in chunks:
                attribution = RagReferenceAttributionSchema(
                    source_name=source_name,
                    source_url=f"fixture://{source_name}",
                    title=parsed.title,
                    section_path=chunk.section_path,
                    language=language,
                    level=level,
                    content_type=chunk.content_type,
                    topics=[],
                    license="fixture-local",
                    external_processing_allowed=True,
                )
                references.append(
                    RagReferenceSchema(
                        chunk_id=chunk.chunk_id,
                        text=chunk.text,
                        source_name=source_name,
                        source_url=f"fixture://{source_name}",
                        title=parsed.title,
                        section_path=chunk.section_path,
                        language=language,
                        level=level,
                        content_type=chunk.content_type,
                        topics=[],
                        license="fixture-local",
                        external_processing_allowed=True,
                        attributions=[attribution],
                    )
                )
        return references

    async def retrieve(
        self,
        query: str,
        language: str | None = None,
        level: str | None = None,
        content_type: str | None = None,
        top_k: int = 8,
    ) -> list[RagReferenceSchema]:
        candidates = [
            reference
            for reference in self.documents
            if (language is None or reference.language == language)
            and (level is None or reference.level == level)
            and (
                content_type is None or reference.content_type == content_type
            )
        ]
        query_tokens = self._tokens(query)
        vector_ranked = sorted(
            candidates,
            key=lambda item: (
                -self._cosine(
                    self._vectorize(query_tokens),
                    self._vectorize(self._tokens(item.text)),
                ),
                item.chunk_id,
            ),
        )
        lexical_ranked = sorted(
            (
                item
                for item in candidates
                if query_tokens & self._tokens(item.text)
            ),
            key=lambda item: (
                -len(query_tokens & self._tokens(item.text)),
                item.chunk_id,
            ),
        )
        ranked = RagRetrievalService.reciprocal_rank_fusion(
            [item.chunk_id for item in vector_ranked],
            [item.chunk_id for item in lexical_ranked],
            k=RagRetrievalService.RRF_CONSTANT,
        )
        candidates_by_id = {item.chunk_id: item for item in candidates}
        ordered = [candidates_by_id[chunk_id] for chunk_id, _score in ranked]
        return ordered[:top_k]

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {token.casefold() for token in _TOKEN_PATTERN.findall(text)}

    @staticmethod
    def _vectorize(tokens: set[str], dimensions: int = 128) -> list[float]:
        vector = [0.0] * dimensions
        for token in tokens:
            digest = hashlib.blake2b(
                token.encode("utf-8"), digest_size=8
            ).digest()
            value = int.from_bytes(digest, byteorder="big")
            index = value % dimensions
            vector[index] += 1.0 if value & (1 << 63) else -1.0
        return vector

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if not left_norm or not right_norm:
            return 0.0
        return dot / (left_norm * right_norm)


async def evaluate_retriever(
    retriever,
    *,
    k: int = 8,
    questions: list[RagEvaluationQuestion] | None = None,
    model_id: str | None = None,
    dimensions: int | None = None,
) -> RagEvaluationReport:
    evaluation_questions = questions or load_evaluation_questions()
    results = []
    for question in evaluation_questions:
        retrieved = await retriever.retrieve(
            question.query,
            language=question.language,
            level=question.level,
            top_k=k,
        )
        recall = recall_at_k(retrieved, question.expected, k)
        results.append(
            {
                "id": question.id,
                "recall_at_k": recall,
                "expected": question.expected,
                "retrieved": [
                    {
                        "source_name": result.source_name,
                        "source_url": result.source_url,
                        "section_path": result.section_path,
                        "chunk_id": result.chunk_id,
                    }
                    for result in retrieved[:k]
                ],
            }
        )
    mean_recall = (
        sum(result["recall_at_k"] for result in results) / len(results)
        if results
        else 0.0
    )
    return RagEvaluationReport(
        k=k,
        mean_recall_at_k=mean_recall,
        questions=results,
        model_id=model_id,
        dimensions=dimensions,
    )


async def run_fixture_evaluation(k: int = 8) -> RagEvaluationReport:
    return await evaluate_retriever(FixtureRagRetriever(), k=k)
