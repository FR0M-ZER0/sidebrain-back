from __future__ import annotations

import logging
from typing import Protocol

from sidebrain_back.core.constants import Env
from sidebrain_back.core.database import async_session
from sidebrain_back.rag.rag_config import load_rag_config
from sidebrain_back.rag.rag_openai_embedding_provider import (
    RagOpenAIEmbeddingProvider,
)
from sidebrain_back.schemas.rag_schema import (
    RagClassificationSchema,
    RagReferenceSchema,
)
from sidebrain_back.services.rag_retrieval_service import RagRetrievalService
from sidebrain_back.services.rag_routing_service import RagRoutingService

logger = logging.getLogger(__name__)


class RagRouter(Protocol):
    def should_use_rag(
        self, goal: str, topic: str
    ) -> RagClassificationSchema: ...


class RagRetriever(Protocol):
    async def retrieve(
        self,
        *,
        query: str,
        language: str,
        level: str | None = None,
        content_type: str | None = None,
        top_k: int = 8,
    ) -> list[RagReferenceSchema]: ...


class RagGenerationContextService:
    def __init__(self, router: RagRouter, retriever: RagRetriever):
        self.router = router
        self.retriever = retriever

    async def get_references(
        self,
        *,
        goal: str | None,
        topic: str | None,
        level: str | None = None,
        content_type: str | None = None,
        top_k: int = 8,
    ) -> list[RagReferenceSchema]:
        if not goal or not topic:
            return []

        try:
            decision = self.router.should_use_rag(goal, topic)
        except Exception as error:
            logger.warning(
                "RAG classification failed; generating without references",
                extra={"error_category": type(error).__name__},
            )
            return []

        if (
            not decision.use_rag
            or decision.language is None
            or decision.confidence < Env.RAG_ROUTER_CONFIDENCE_THRESHOLD
        ):
            return []

        context_level = self._normalize_level(level)
        try:
            references = await self.retriever.retrieve(
                query=f"Objetivo: {goal}\nTópico: {topic}",
                language=decision.language,
                level=context_level,
                content_type=content_type,
                top_k=top_k,
            )
        except Exception as error:
            logger.warning(
                "RAG retrieval failed; generating without references",
                extra={"error_category": type(error).__name__},
            )
            return []

        permitted_references = []
        for reference in references:
            if not reference.external_processing_allowed:
                continue
            permitted_attributions = [
                attribution
                for attribution in reference.attributions
                if attribution.external_processing_allowed
            ]
            permitted_references.append(
                reference.model_copy(
                    update={"attributions": permitted_attributions}
                )
            )
        return permitted_references

    async def aclose(self) -> None:
        provider = getattr(self.retriever, "embedding_provider", None)
        close = getattr(provider, "aclose", None)
        if close is not None:
            await close()

    @staticmethod
    def _normalize_level(level: str | None) -> str | None:
        if level is None:
            return None
        if level == "pro":
            return "advanced"
        if level in {"beginner", "intermediate", "advanced"}:
            return level
        return None


def build_rag_generation_context_service() -> (
    RagGenerationContextService | None
):
    try:
        config = load_rag_config()
        provider = RagOpenAIEmbeddingProvider()
        retrieval_service = RagRetrievalService(
            session_factory=async_session,
            embedding_provider=provider,
            embedding_config=config.defaults.embeddings,
        )
        return RagGenerationContextService(
            RagRoutingService(),
            retrieval_service,
        )
    except Exception as error:
        logger.warning(
            "RAG context service unavailable; generation will continue "
            "without references",
            extra={"error_category": type(error).__name__},
        )
        return None
