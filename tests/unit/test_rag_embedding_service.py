import asyncio
from types import SimpleNamespace

from sidebrain_back.rag.rag_config import RagEmbeddingConfig
from sidebrain_back.rag.rag_openai_embedding_provider import (
    RagEmbeddingConfigurationError,
    RagOpenAIEmbeddingProvider,
)
from sidebrain_back.services.rag_embedding_service import (
    RagEmbeddingInput,
    RagEmbeddingService,
)


class FakeTokenizer:
    def count(self, text: str) -> int:
        return len(text.split())


class FakeRepository:
    def __init__(self, cached_by_hash=None):
        self.cached_by_hash = cached_by_hash or {}
        self.current = {}
        self.created = []

    async def get_embedding(self, chunk_id, model_id, dimensions):
        return self.current.get((chunk_id, model_id, dimensions))

    async def get_cached_embedding_by_content_hash(
        self, content_hash, model_id, dimensions
    ):
        return self.cached_by_hash.get((content_hash, model_id, dimensions))

    async def create_embedding(self, **values):
        self.created.append(values)
        result = SimpleNamespace(**values)
        self.current[
            (values["chunk_id"], values["model_id"], values["dimensions"])
        ] = result
        return result


class FakeProvider:
    def __init__(self, dimensions=1536, failures=None, input_tokens=None):
        self.dimensions = dimensions
        self.failures = list(failures or [])
        self.input_tokens = input_tokens
        self.batches = []

    async def embed_texts(self, texts, *, model, dimensions):
        self.batches.append((list(texts), model, dimensions))
        if self.failures:
            error = self.failures.pop(0)
            raise error
        vectors = [
            [float(index)] * self.dimensions for index, _ in enumerate(texts)
        ]
        input_tokens = self.input_tokens or sum(
            len(text.split()) for text in texts
        )
        return vectors, input_tokens


class FakeRateLimitError(Exception):
    status_code = 429
    response = SimpleNamespace(headers={"retry-after": "0"})


def _config(**updates):
    values = {
        "model": "test-embedding-model",
        "dimensions": 1536,
        "batch_size": 2,
        "max_attempts": 3,
        "max_input_tokens": 8,
        "max_batch_tokens": 12,
        "price_per_million_input_tokens": 2.0,
    }
    values.update(updates)
    return RagEmbeddingConfig.model_validate(values)


def _chunk(chunk_id, content_hash=None, text="one two", allowed=True):
    return RagEmbeddingInput(
        chunk_id=chunk_id,
        content_hash=content_hash or chunk_id,
        text=text,
        external_processing_allowed=allowed,
    )


def test_embedding_service_batches_and_reports_configured_cost():
    provider = FakeProvider(dimensions=1536)
    repository = FakeRepository()
    service = RagEmbeddingService(
        provider=provider,
        tokenizer=FakeTokenizer(),
        repository=repository,
        config=_config(),
    )

    results, usage = asyncio.run(
        service.embed_chunks(
            [
                _chunk("a", text="one two"),
                _chunk("b", text="three four"),
                _chunk("c", text="five six"),
            ]
        )
    )

    assert [len(batch[0]) for batch in provider.batches] == [2, 1]
    assert len(results) == 3
    assert usage.input_tokens == 6
    assert usage.estimated_cost == 0.000012
    assert len(repository.created) == 3


def test_embedding_service_retries_only_transient_provider_errors():
    provider = FakeProvider(
        dimensions=1536,
        failures=[FakeRateLimitError("rate limited")],
    )
    repository = FakeRepository()
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    service = RagEmbeddingService(
        provider=provider,
        tokenizer=FakeTokenizer(),
        repository=repository,
        config=_config(),
        sleep=fake_sleep,
    )

    results, usage = asyncio.run(service.embed_chunks([_chunk("a")]))

    assert len(provider.batches) == 2
    assert len(delays) == 1
    assert results[0].vector == [0.0] * 1536
    assert usage.retries == 1


def test_embedding_service_uses_hash_cache_and_skips_unapproved_or_oversized():
    cached = SimpleNamespace(
        embedding=[0.1] * 1536,
        input_tokens=2,
        tokenizer_id="cl100k_base",
        chunker_version="1",
    )
    repository = FakeRepository(
        cached_by_hash={
            ("same-content", "test-embedding-model", 1536): cached,
        }
    )
    provider = FakeProvider(dimensions=1536)
    service = RagEmbeddingService(
        provider=provider,
        tokenizer=FakeTokenizer(),
        repository=repository,
        config=_config(max_input_tokens=3),
    )

    results, usage = asyncio.run(
        service.embed_chunks(
            [
                _chunk("cached-copy", content_hash="same-content"),
                _chunk("too-long", text="one two three four"),
                _chunk("license-unknown", allowed=False),
            ]
        )
    )

    assert [result.cached for result in results] == [True, False, False]
    assert [result.skip_reason for result in results] == [
        None,
        "input_too_long",
        "external_processing_not_allowed",
    ]
    assert provider.batches == []
    assert len(repository.created) == 1
    assert usage.input_tokens == 0


def test_openai_provider_sorts_batch_results_and_reports_usage():
    class FakeEmbeddings:
        def __init__(self):
            self.request = None

        async def create(self, **kwargs):
            self.request = kwargs
            return SimpleNamespace(
                data=[
                    SimpleNamespace(index=1, embedding=[4.0, 5.0, 6.0]),
                    SimpleNamespace(index=0, embedding=[1.0, 2.0, 3.0]),
                ],
                usage=SimpleNamespace(prompt_tokens=7),
            )

    embeddings = FakeEmbeddings()
    client = SimpleNamespace(embeddings=embeddings)
    provider = RagOpenAIEmbeddingProvider(api_key="test-key", client=client)

    vectors, input_tokens = asyncio.run(
        provider.embed_texts(
            ["first", "second"], model="test-model", dimensions=3
        )
    )

    assert vectors == [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    assert input_tokens == 7
    assert embeddings.request["dimensions"] == 3


def test_openai_provider_requires_key_only_when_embedding_is_requested():
    provider = RagOpenAIEmbeddingProvider(api_key="")

    try:
        asyncio.run(
            provider.embed_texts(["one"], model="test-model", dimensions=3)
        )
    except RagEmbeddingConfigurationError as error:
        assert "OPENAI_API_KEY" in str(error)
    else:
        raise AssertionError(
            "missing key must fail only when embedding is used"
        )
