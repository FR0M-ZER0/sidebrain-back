from contextlib import asynccontextmanager

import pytest
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.models.rag_chunk_attribution_model import (
    RagChunkAttributionModel,
)
from sidebrain_back.models.rag_chunk_embedding_model import (
    RagChunkEmbeddingModel,
)
from sidebrain_back.models.rag_chunk_model import RagChunkModel
from sidebrain_back.models.rag_document_model import RagDocumentModel
from sidebrain_back.rag.rag_config import load_rag_config
from sidebrain_back.services.rag_retrieval_service import RagRetrievalService


class FixtureQueryEmbeddingProvider:
    async def embed_texts(self, texts, *, model, dimensions):
        return [[0.01] * dimensions for _ in texts], len(texts)


def _add_chunk(
    db: AsyncSession,
    *,
    chunk_id: str,
    document_id: str,
    language: str,
    level: str,
    content_type: str,
    text: str,
) -> None:
    source_name = f"{language}-{chunk_id}"
    url = f"https://docs.example/{chunk_id}"
    db.add(
        RagDocumentModel(
            doc_id=document_id,
            source_name=source_name,
            source_url=url,
            canonical_url=url,
            title=f"Document {chunk_id}",
            document_hash=chunk_id,
        )
    )
    db.add(
        RagChunkModel(
            chunk_id=chunk_id,
            content_hash=chunk_id,
            text=text,
            search_vector=func.to_tsvector("simple", text),
        )
    )
    db.add(
        RagChunkAttributionModel(
            chunk_id=chunk_id,
            doc_id=document_id,
            section_path=f"{language.title()} > {chunk_id}",
            source_name=source_name,
            source_url=url,
            title=f"Document {chunk_id}",
            language=language,
            level=level,
            content_type=content_type,
            topics=["fixture"],
            license="fixture-license",
            external_processing_allowed=True,
        )
    )
    db.add(
        RagChunkEmbeddingModel(
            chunk_id=chunk_id,
            model_id="text-embedding-3-small",
            dimensions=1536,
            embedding=[0.01] * 1536,
            tokenizer_id="cl100k_base",
            chunker_version="1",
            input_tokens=5,
        )
    )


@pytest.mark.anyio
async def test_postgres_hybrid_retrieval_applies_filters_to_both_searches(
    db_session: AsyncSession,
):
    _add_chunk(
        db_session,
        chunk_id="1" * 64,
        document_id="a" * 64,
        language="python",
        level="beginner",
        content_type="concept",
        text="Python variables bind names to values.",
    )
    _add_chunk(
        db_session,
        chunk_id="2" * 64,
        document_id="b" * 64,
        language="python",
        level="advanced",
        content_type="reference",
        text="Python generators yield values lazily.",
    )
    _add_chunk(
        db_session,
        chunk_id="3" * 64,
        document_id="c" * 64,
        language="javascript",
        level="advanced",
        content_type="reference",
        text="JavaScript closures preserve lexical scope.",
    )
    await db_session.flush()

    @asynccontextmanager
    async def session_factory():
        yield db_session

    config = load_rag_config()
    service = RagRetrievalService(
        session_factory=session_factory,
        embedding_provider=FixtureQueryEmbeddingProvider(),
        embedding_config=config.defaults.embeddings,
    )

    beginner_results = await service.retrieve(
        "Python variables",
        language="python",
        level="beginner",
        content_type="concept",
    )
    advanced_results = await service.retrieve(
        "JavaScript closures",
        language="javascript",
        level="pro",
        content_type="reference",
    )

    assert [result.chunk_id for result in beginner_results] == ["1" * 64]
    assert [result.chunk_id for result in advanced_results] == ["3" * 64]
    assert beginner_results[0].source_url == "https://docs.example/" + "1" * 64
