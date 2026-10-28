from collections.abc import Callable
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.models.rag_chunk_attribution_model import (
    RagChunkAttributionModel,
)
from sidebrain_back.models.rag_chunk_embedding_model import (
    RagChunkEmbeddingModel,
)
from sidebrain_back.models.rag_chunk_model import RagChunkModel
from sidebrain_back.models.rag_document_model import RagDocumentModel
from sidebrain_back.rag.rag_chunker import RagChunker
from sidebrain_back.rag.rag_config import (
    RagConfig,
    RagContentLicenseConfig,
    RagSourceConfig,
    RagSourceType,
    load_rag_config,
)
from sidebrain_back.rag.rag_local_connector import RagLocalConnector
from sidebrain_back.rag.rag_tokenizer import RagTokenizer
from sidebrain_back.repositories.rag_chunk_repository import RagChunkRepository
from sidebrain_back.repositories.rag_document_repository import (
    RagDocumentRepository,
)
from sidebrain_back.services.rag_embedding_service import RagEmbeddingService
from sidebrain_back.services.rag_indexing_service import RagIndexingService


class FixtureEmbeddingProvider:
    def __init__(self):
        self.calls = 0

    async def embed_texts(self, texts, *, model: str, dimensions: int):
        self.calls += 1
        return [[0.01] * dimensions for _ in texts], sum(
            len(text.split()) for text in texts
        )


def _source(name: str, path: Path) -> RagSourceConfig:
    return RagSourceConfig(
        name=name,
        type=RagSourceType.LOCAL,
        path=str(path),
        language="python",
        level="beginner",
        license="PSF-2.0",
        license_url="https://docs.python.org/3/license.html",
        content_licenses={
            "prose": RagContentLicenseConfig(
                license="PSF-2.0",
                license_url="https://docs.python.org/3/license.html",
                external_processing_allowed=True,
            ),
            "code_example": RagContentLicenseConfig(
                license="0BSD",
                license_url="https://docs.python.org/3/license.html",
                external_processing_allowed=True,
            ),
        },
        include_paths=["**/*.md"],
        exclude_paths=["private/**"],
        version_strategy="content_hash",
        connector={},
    )


def _service(
    db: AsyncSession,
    config: RagConfig,
    provider: FixtureEmbeddingProvider,
) -> RagIndexingService:
    chunk_repository = RagChunkRepository(db)
    tokenizer = RagTokenizer(config.defaults.chunking.encoding)
    embedding_service = RagEmbeddingService(
        provider=provider,
        tokenizer=tokenizer,
        repository=chunk_repository,
        config=config.defaults.embeddings,
    )
    return RagIndexingService(
        db=db,
        document_repository=RagDocumentRepository(db),
        chunk_repository=chunk_repository,
        chunker=RagChunker(
            tokenizer=tokenizer,
            target_tokens=config.defaults.chunking.target_tokens,
            overlap_ratio=config.defaults.chunking.overlap_ratio,
        ),
        embedding_service=embedding_service,
        config=config,
        local_connector=RagLocalConnector(),
    )


async def _count(db: AsyncSession, model) -> int:
    return int(await db.scalar(select(func.count()).select_from(model)) or 0)


async def _exercise_source_scope(
    db: AsyncSession,
    root: Path,
    source_factory: Callable[[str, Path], RagSourceConfig],
):
    config = load_rag_config()
    provider = FixtureEmbeddingProvider()
    first_source = source_factory("local-python-one", root)
    second_source = source_factory("local-python-two", root)
    first_service = _service(db, config, provider)
    second_service = _service(db, config, provider)

    first_report = await first_service.index_source(first_source)
    second_report = await second_service.index_source(second_source)
    assert first_report.documents_processed == 1
    assert second_report.documents_processed == 1
    assert provider.calls == 1
    assert await _count(db, RagDocumentModel) == 2
    assert await _count(db, RagChunkAttributionModel) >= 2
    assert await _count(db, RagChunkEmbeddingModel) == 1

    (root / "tutorial.md").unlink()
    removal_report = await first_service.index_source(first_source)

    assert removal_report.documents_found == 0
    assert await _count(db, RagDocumentModel) == 1
    assert await _count(db, RagChunkAttributionModel) >= 1
    assert await _count(db, RagChunkModel) == 1
    assert await _count(db, RagChunkEmbeddingModel) == 1


@pytest.mark.anyio
async def test_incremental_local_index_preserves_other_source_provenance(
    db_session: AsyncSession,
    tmp_path: Path,
):
    (tmp_path / "tutorial.md").write_text(
        """# Python Tutorial

## Lists

Lists preserve insertion order and can be indexed.

```python
items = [1, 2, 3]
```
""",
        encoding="utf-8",
    )

    await _exercise_source_scope(db_session, tmp_path, _source)
