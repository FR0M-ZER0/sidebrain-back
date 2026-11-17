from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Protocol

from sidebrain_back.core.constants import RAG_VECTOR_DIMENSIONS
from sidebrain_back.rag.rag_config import RagEmbeddingConfig
from sidebrain_back.rag.rag_tokenizer import Tokenizer
from sidebrain_back.repositories.rag_chunk_repository import RagChunkRepository


class EmbeddingProvider(Protocol):
    async def embed_texts(
        self, texts: list[str], *, model: str, dimensions: int
    ) -> tuple[list[list[float]], int]: ...


@dataclass(frozen=True)
class RagEmbeddingInput:
    chunk_id: str
    content_hash: str
    text: str
    external_processing_allowed: bool


@dataclass(frozen=True)
class RagEmbeddingResult:
    chunk_id: str
    vector: list[float] | None
    input_tokens: int
    cached: bool
    skip_reason: str | None = None


@dataclass(frozen=True)
class RagEmbeddingUsage:
    input_tokens: int
    estimated_cost: float | None
    batches: int
    retries: int
    cached_chunks: int
    skipped_chunks: int


class RagEmbeddingError(RuntimeError):
    pass


class RagEmbeddingService:
    def __init__(
        self,
        *,
        provider: EmbeddingProvider,
        tokenizer: Tokenizer,
        repository: RagChunkRepository,
        config: RagEmbeddingConfig,
        sleep=asyncio.sleep,
        random_value=random.random,
    ):
        self.provider = provider
        self.tokenizer = tokenizer
        self.repository = repository
        self.config = config
        self.tokenizer_id = getattr(tokenizer, "encoding_name", "unknown")
        self.sleep = sleep
        self.random_value = random_value

    def validate_configuration(self) -> None:
        if self.config.dimensions != RAG_VECTOR_DIMENSIONS:
            raise RagEmbeddingError(
                "configured embedding dimensions do not match the migrated "
                "vector column"
            )
        validate_provider = getattr(
            self.provider, "validate_configuration", None
        )
        if validate_provider is not None:
            validate_provider()

    async def embed_chunks(
        self, chunks: list[RagEmbeddingInput]
    ) -> tuple[list[RagEmbeddingResult], RagEmbeddingUsage]:
        if self.config.dimensions != RAG_VECTOR_DIMENSIONS:
            raise RagEmbeddingError(
                "configured embedding dimensions do not match the migrated "
                "vector column"
            )
        results: dict[str, RagEmbeddingResult] = {}
        pending: list[tuple[RagEmbeddingInput, int]] = []
        cached_copies: list[tuple[RagEmbeddingInput, object, int]] = []
        cache_count = 0
        skipped_count = 0

        for chunk in chunks:
            if not chunk.external_processing_allowed:
                results[chunk.chunk_id] = RagEmbeddingResult(
                    chunk_id=chunk.chunk_id,
                    vector=None,
                    input_tokens=0,
                    cached=False,
                    skip_reason="external_processing_not_allowed",
                )
                skipped_count += 1
                continue

            current = await self.repository.get_embedding(
                chunk.chunk_id,
                self.config.model,
                self.config.dimensions,
            )
            if current is not None:
                results[chunk.chunk_id] = RagEmbeddingResult(
                    chunk_id=chunk.chunk_id,
                    vector=list(current.embedding),
                    input_tokens=current.input_tokens,
                    cached=True,
                )
                cache_count += 1
                continue

            cached = (
                await self.repository.get_cached_embedding_by_content_hash(
                    chunk.content_hash,
                    self.config.model,
                    self.config.dimensions,
                )
            )
            if cached is not None:
                cached_copies.append((chunk, cached, int(cached.input_tokens)))
                results[chunk.chunk_id] = RagEmbeddingResult(
                    chunk_id=chunk.chunk_id,
                    vector=list(cached.embedding),
                    input_tokens=cached.input_tokens,
                    cached=True,
                )
                cache_count += 1
                continue

            input_tokens = self.tokenizer.count(chunk.text)
            if input_tokens > self.config.max_input_tokens:
                results[chunk.chunk_id] = RagEmbeddingResult(
                    chunk_id=chunk.chunk_id,
                    vector=None,
                    input_tokens=input_tokens,
                    cached=False,
                    skip_reason="input_too_long",
                )
                skipped_count += 1
                continue
            pending.append((chunk, input_tokens))

        batches = self._make_batches(pending)
        total_tokens = 0
        retry_count = 0
        if pending or cached_copies:
            await self._repository_action("release_read_transaction")
        try:
            for chunk, cached, cached_tokens in cached_copies:
                await self.repository.create_embedding(
                    chunk_id=chunk.chunk_id,
                    model_id=self.config.model,
                    dimensions=self.config.dimensions,
                    embedding=list(cached.embedding),
                    tokenizer_id=self.tokenizer_id,
                    chunker_version="1",
                    input_tokens=cached_tokens,
                )
            if cached_copies:
                await self._repository_action("commit")

            for batch in batches:
                vectors, usage_tokens, retries = await self._embed_batch(batch)
                retry_count += retries
                total_tokens += usage_tokens
                for (chunk, input_tokens), vector in zip(
                    batch, vectors, strict=True
                ):
                    if len(vector) != self.config.dimensions:
                        raise RagEmbeddingError(
                            "embedding response dimension does not match "
                            "configuration"
                        )
                    record = await self.repository.create_embedding(
                        chunk_id=chunk.chunk_id,
                        model_id=self.config.model,
                        dimensions=self.config.dimensions,
                        embedding=vector,
                        tokenizer_id=self.tokenizer_id,
                        chunker_version="1",
                        input_tokens=input_tokens,
                    )
                    results[chunk.chunk_id] = RagEmbeddingResult(
                        chunk_id=chunk.chunk_id,
                        vector=list(record.embedding),
                        input_tokens=input_tokens,
                        cached=False,
                    )
                await self._repository_action("commit")
        except Exception:
            await self._repository_action("rollback")
            raise

        price = self.config.price_per_million_input_tokens
        estimated_cost = (
            total_tokens * price / 1_000_000 if price is not None else None
        )
        ordered_results = [results[chunk.chunk_id] for chunk in chunks]
        return ordered_results, RagEmbeddingUsage(
            input_tokens=total_tokens,
            estimated_cost=estimated_cost,
            batches=len(batches),
            retries=retry_count,
            cached_chunks=cache_count,
            skipped_chunks=skipped_count,
        )

    def _make_batches(
        self, pending: list[tuple[RagEmbeddingInput, int]]
    ) -> list[list[tuple[RagEmbeddingInput, int]]]:
        batches: list[list[tuple[RagEmbeddingInput, int]]] = []
        current: list[tuple[RagEmbeddingInput, int]] = []
        current_tokens = 0
        for item in pending:
            item_tokens = item[1]
            if current and (
                len(current) >= self.config.batch_size
                or current_tokens + item_tokens > self.config.max_batch_tokens
            ):
                batches.append(current)
                current = []
                current_tokens = 0
            current.append(item)
            current_tokens += item_tokens
        if current:
            batches.append(current)
        return batches

    async def _embed_batch(
        self, batch: list[tuple[RagEmbeddingInput, int]]
    ) -> tuple[list[list[float]], int, int]:
        texts = [chunk.text for chunk, _ in batch]
        retries = 0
        for attempt in range(self.config.max_attempts):
            try:
                vectors, input_tokens = await self.provider.embed_texts(
                    texts,
                    model=self.config.model,
                    dimensions=self.config.dimensions,
                )
                if len(vectors) != len(batch):
                    raise RagEmbeddingError(
                        "embedding response count does not match request"
                    )
                estimated_tokens = sum(tokens for _, tokens in batch)
                return vectors, input_tokens or estimated_tokens, retries
            except Exception as error:
                if (
                    attempt + 1 >= self.config.max_attempts
                    or not self._is_retryable(error)
                ):
                    raise RagEmbeddingError(
                        f"embedding batch failed ({type(error).__name__})"
                    ) from None
                retries += 1
                await self.sleep(self._retry_delay(error, attempt))
        raise RagEmbeddingError("embedding batch exhausted retries")

    def _retry_delay(self, error: Exception, attempt: int) -> float:
        response = getattr(error, "response", None)
        headers = getattr(response, "headers", {})
        retry_after = headers.get("retry-after") if headers else None
        if retry_after is not None:
            try:
                return min(30.0, max(0.0, float(retry_after)))
            except (TypeError, ValueError):
                try:
                    retry_at = parsedate_to_datetime(retry_after).timestamp()
                    return min(30.0, max(0.0, retry_at - time.time()))
                except (TypeError, ValueError, OverflowError):
                    pass
        exponential = min(30.0, 0.5 * (2**attempt))
        return exponential + self.random_value() * min(0.5, exponential / 4)

    async def _repository_action(self, name: str) -> None:
        action = getattr(self.repository, name, None)
        if action is not None:
            await action()

    @staticmethod
    def _is_retryable(error: Exception) -> bool:
        status_code = getattr(error, "status_code", None)
        if status_code is None:
            response = getattr(error, "response", None)
            status_code = getattr(response, "status_code", None)
        if status_code in {408, 409, 429}:
            return True
        if isinstance(status_code, int) and status_code >= 500:
            return True
        return isinstance(error, (TimeoutError, ConnectionError)) or type(
            error
        ).__name__ in {
            "APIConnectionError",
            "APITimeoutError",
            "InternalServerError",
            "RateLimitError",
        }
