from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from sidebrain_back.core.constants import Env


class RagEmbeddingConfigurationError(RuntimeError):
    """Raised when an embedding operation lacks optional credentials."""


class RagOpenAIEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: Any | None = None,
        timeout_seconds: float = 30,
    ):
        self.api_key = api_key
        self.client = client
        self.timeout_seconds = timeout_seconds

    def validate_configuration(self) -> None:
        self._get_client()

    async def embed_texts(
        self,
        texts: list[str],
        *,
        model: str,
        dimensions: int,
    ) -> tuple[list[list[float]], int]:
        if not texts:
            return [], 0
        client = self._get_client()
        response = await client.embeddings.create(
            input=texts,
            model=model,
            dimensions=dimensions,
            encoding_format="float",
        )
        items = sorted(response.data, key=lambda item: item.index)
        if len(items) != len(texts) or [item.index for item in items] != list(
            range(len(texts))
        ):
            raise ValueError(
                "embedding provider returned invalid item ordering"
            )
        vectors = [list(item.embedding) for item in items]
        if any(len(vector) != dimensions for vector in vectors):
            raise ValueError("embedding provider returned invalid dimensions")
        return vectors, int(response.usage.prompt_tokens or 0)

    async def aclose(self) -> None:
        if self.client is not None:
            close = getattr(self.client, "close", None)
            async_close = getattr(self.client, "aclose", None)
            if async_close is not None:
                await async_close()
            elif close is not None:
                await close()
            self.client = None

    def _get_client(self) -> Any:
        if self.client is not None:
            return self.client
        api_key = (
            self.api_key
            if self.api_key is not None
            else Env.OPENAI_API_KEY
        )
        if not api_key or not api_key.strip():
            raise RagEmbeddingConfigurationError(
                "OPENAI_API_KEY is required for embedding operations"
            )
        self.client = AsyncOpenAI(
            api_key=api_key,
            max_retries=0,
            timeout=self.timeout_seconds,
        )
        return self.client
