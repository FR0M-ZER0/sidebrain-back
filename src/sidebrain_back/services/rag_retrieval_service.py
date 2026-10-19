from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from sidebrain_back.core.constants import RAG_VECTOR_DIMENSIONS
from sidebrain_back.rag.rag_config import RagEmbeddingConfig
from sidebrain_back.repositories.rag_chunk_repository import RagChunkRepository
from sidebrain_back.schemas.rag_schema import (
    RagContentType,
    RagLanguage,
    RagLevel,
    RagReferenceAttributionSchema,
    RagReferenceSchema,
)
from sidebrain_back.services.rag_embedding_service import EmbeddingProvider


class RagRetrievalService:
    """Combines PostgreSQL vector and lexical candidates with RRF.

    RRF uses the constant ``k=60`` and retrieves 50 candidates from each
    search branch before merging. An optional reranker can be injected, but is
    disabled unless explicitly supplied.
    """

    RRF_CONSTANT = 60
    CANDIDATE_LIMIT = 50

    def __init__(
        self,
        *,
        session_factory: Callable,
        embedding_provider: EmbeddingProvider,
        embedding_config: RagEmbeddingConfig,
        repository_factory: Callable[[Any], RagChunkRepository] = (
            RagChunkRepository
        ),
        reranker: Callable | None = None,
    ):
        self.session_factory = session_factory
        self.embedding_provider = embedding_provider
        self.embedding_config = embedding_config
        self.repository_factory = repository_factory
        self.reranker = reranker

    async def retrieve(
        self,
        query: str,
        language: RagLanguage | None = None,
        level: RagLevel | str | None = None,
        content_type: RagContentType | None = None,
        top_k: int = 8,
    ) -> list[RagReferenceSchema]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if not 1 <= top_k <= 50:
            raise ValueError("top_k must be between 1 and 50")
        normalized_level = self._normalize_level(level)
        if self.embedding_config.dimensions != RAG_VECTOR_DIMENSIONS:
            raise ValueError(
                "configured embedding dimensions do not match the migrated "
                "vector column"
            )

        query_vectors, _input_tokens = await (
            self.embedding_provider.embed_texts(
                [query],
                model=self.embedding_config.model,
                dimensions=self.embedding_config.dimensions,
            )
        )
        if (
            len(query_vectors) != 1
            or len(query_vectors[0]) != RAG_VECTOR_DIMENSIONS
        ):
            raise ValueError("query embedding has invalid dimensions")

        async with self.session_factory() as db:
            repository = self.repository_factory(db)
            vector_candidates = await repository.search_vector_candidates(
                embedding=query_vectors[0],
                model_id=self.embedding_config.model,
                dimensions=self.embedding_config.dimensions,
                language=language,
                level=normalized_level,
                content_type=content_type,
                limit=self.CANDIDATE_LIMIT,
            )
            text_candidates = await repository.search_text_candidates(
                query=query,
                language=language,
                level=normalized_level,
                content_type=content_type,
                limit=self.CANDIDATE_LIMIT,
            )
            vector_ids = self._unique_ids(vector_candidates)
            text_ids = self._unique_ids(text_candidates)
            ranked = self.reciprocal_rank_fusion(
                vector_ids, text_ids, k=self.RRF_CONSTANT
            )
            chunks_by_id = {
                chunk.chunk_id: chunk
                for chunk in [*vector_candidates, *text_candidates]
            }
            groups: dict[str, list[tuple[Any, float]]] = defaultdict(list)
            for chunk_id, score in ranked:
                chunk = chunks_by_id[chunk_id]
                group_id = chunk.duplicate_group_id or chunk.chunk_id
                groups[group_id].append((chunk, score))

            group_chunk_ids = [
                chunk.chunk_id
                for candidates in groups.values()
                for chunk, _score in candidates
            ]
            attributions = await repository.list_attributions_by_chunk_ids(
                chunk_ids=group_chunk_ids,
                language=language,
                level=normalized_level,
                content_type=content_type,
            )

        attribution_by_chunk: dict[str, list[Any]] = defaultdict(list)
        for attribution in attributions:
            attribution_by_chunk[attribution.chunk_id].append(attribution)

        results: list[RagReferenceSchema] = []
        for candidates in groups.values():
            selected_chunk, selected_score = candidates[0]
            source_attributions = self._deduplicate_attributions(
                [
                    attribution
                    for chunk, _score in candidates
                    for attribution in attribution_by_chunk[chunk.chunk_id]
                ]
            )
            if not source_attributions:
                continue
            primary = next(
                (
                    item
                    for item in source_attributions
                    if item.external_processing_allowed
                ),
                source_attributions[0],
            )
            attribution_schemas = [
                RagReferenceAttributionSchema(
                    source_name=item.source_name,
                    source_url=item.source_url,
                    title=item.title,
                    section_path=item.section_path,
                    language=item.language,
                    level=item.level,
                    content_type=item.content_type,
                    topics=list(item.topics or []),
                    license=item.license,
                    license_url=item.license_url,
                    external_processing_allowed=(
                        item.external_processing_allowed
                    ),
                )
                for item in source_attributions
            ]
            results.append(
                RagReferenceSchema(
                    chunk_id=selected_chunk.chunk_id,
                    text=selected_chunk.text,
                    source_name=primary.source_name,
                    source_url=primary.source_url,
                    title=primary.title,
                    section_path=primary.section_path,
                    language=primary.language,
                    level=primary.level,
                    content_type=primary.content_type,
                    topics=list(primary.topics or []),
                    license=primary.license,
                    license_url=primary.license_url,
                    external_processing_allowed=(
                        primary.external_processing_allowed
                    ),
                    attributions=attribution_schemas,
                    score=max(score for _chunk, score in candidates),
                )
            )
        results.sort(
            key=lambda result: (-(result.score or 0), result.chunk_id)
        )
        if self.reranker is not None:
            reranked = self.reranker(query, results)
            if hasattr(reranked, "__await__"):
                reranked = await reranked
            results = list(reranked)
        return results[:top_k]

    @staticmethod
    def reciprocal_rank_fusion(
        vector_ids: list[str],
        text_ids: list[str],
        *,
        k: int = 60,
    ) -> list[tuple[str, float]]:
        scores: dict[str, float] = defaultdict(float)
        for ranked_ids in (vector_ids, text_ids):
            for rank, chunk_id in enumerate(ranked_ids, start=1):
                scores[chunk_id] += 1.0 / (k + rank)
        return sorted(
            scores.items(), key=lambda result: (-result[1], result[0])
        )

    @staticmethod
    def _unique_ids(chunks: list[Any]) -> list[str]:
        seen: set[str] = set()
        result = []
        for chunk in chunks:
            if chunk.chunk_id not in seen:
                seen.add(chunk.chunk_id)
                result.append(chunk.chunk_id)
        return result

    @staticmethod
    def _normalize_level(level: RagLevel | str | None) -> str | None:
        if level == "pro":
            return "advanced"
        return level

    @staticmethod
    def _deduplicate_attributions(attributions: list[Any]) -> list[Any]:
        result = []
        seen = set()
        for attribution in attributions:
            key = (
                attribution.source_name,
                attribution.source_url,
                attribution.title,
                attribution.section_path,
                attribution.license,
            )
            if key not in seen:
                seen.add(key)
                result.append(attribution)
        return result
