import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from sidebrain_back.rag.rag_config import load_rag_config
from sidebrain_back.services.rag_retrieval_service import RagRetrievalService


class FakeEmbeddingProvider:
    async def embed_texts(self, texts, *, model, dimensions):
        return [[0.1] * dimensions for _ in texts], len(texts)


class FakeRepository:
    def __init__(self, vector_hits, text_hits, attributions):
        self.vector_hits = vector_hits
        self.text_hits = text_hits
        self.attributions = attributions
        self.vector_filters = None
        self.text_filters = None
        self.attribution_filters = None

    async def search_vector_candidates(self, **kwargs):
        self.vector_filters = kwargs
        return self.vector_hits

    async def search_text_candidates(self, **kwargs):
        self.text_filters = kwargs
        return self.text_hits

    async def list_attributions_by_chunk_ids(self, **kwargs):
        self.attribution_filters = kwargs
        return self.attributions


def _candidate(chunk_id: str, duplicate_group_id: str | None = None):
    return SimpleNamespace(
        chunk_id=chunk_id,
        content_hash=chunk_id,
        text=f"Reference {chunk_id}",
        duplicate_group_id=duplicate_group_id,
    )


def _attribution(chunk_id: str, source_name="python-library"):
    return SimpleNamespace(
        chunk_id=chunk_id,
        source_name=source_name,
        source_url=f"https://docs.example/{chunk_id}",
        title="Reference title",
        section_path="Python > Reference",
        language="python",
        level="advanced",
        content_type="reference",
        topics=["async"],
        license="PSF-2.0",
        license_url="https://docs.python.org/3/license.html",
        external_processing_allowed=True,
    )


def _session_factory():
    @asynccontextmanager
    async def session():
        yield object()

    return session


def test_rrf_combines_ranks_and_promotes_a_hit_in_both_lists():
    ranks = RagRetrievalService.reciprocal_rank_fusion(
        ["vector-first", "shared", "vector-third"],
        ["text-first", "shared", "text-third"],
        k=60,
    )

    assert ranks[0][0] == "shared"
    assert ranks[0][1] == 2 / 62
    assert ranks[1][1] == 1 / 61


def test_retrieval_applies_same_filters_and_returns_provenance():
    chunk = _candidate("chunk-1")
    attribution = _attribution("chunk-1")
    repository = FakeRepository(
        vector_hits=[chunk],
        text_hits=[chunk],
        attributions=[attribution],
    )
    config = load_rag_config()
    service = RagRetrievalService(
        session_factory=_session_factory(),
        embedding_provider=FakeEmbeddingProvider(),
        embedding_config=config.defaults.embeddings,
        repository_factory=lambda _db: repository,
    )

    results = asyncio.run(
        service.retrieve(
            "Como funciona async em Python?",
            language="python",
            level="pro",
            content_type="reference",
            top_k=4,
        )
    )

    assert len(results) == 1
    assert results[0].source_url == attribution.source_url
    assert results[0].attributions[0].source_url == attribution.source_url
    assert results[0].score == 2 / 61
    for filters in (
        repository.vector_filters,
        repository.text_filters,
        repository.attribution_filters,
    ):
        assert filters["language"] == "python"
        assert filters["level"] == "advanced"
        assert filters["content_type"] == "reference"


def test_retrieval_collapses_approximate_group_but_merges_attributions():
    first = _candidate("chunk-a", duplicate_group_id="near-duplicate")
    second = _candidate("chunk-b", duplicate_group_id="near-duplicate")
    first_attribution = _attribution("chunk-a", "python-tutorial")
    second_attribution = _attribution("chunk-b", "python-library")
    repository = FakeRepository(
        vector_hits=[first, second],
        text_hits=[second, first],
        attributions=[first_attribution, second_attribution],
    )
    config = load_rag_config()
    service = RagRetrievalService(
        session_factory=_session_factory(),
        embedding_provider=FakeEmbeddingProvider(),
        embedding_config=config.defaults.embeddings,
        repository_factory=lambda _db: repository,
    )

    results = asyncio.run(
        service.retrieve("Python reference", language="python", top_k=8)
    )

    assert len(results) == 1
    assert {item.source_name for item in results[0].attributions} == {
        "python-tutorial",
        "python-library",
    }
