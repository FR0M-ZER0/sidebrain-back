from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import and_, delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sidebrain_back.core.database import get_db
from sidebrain_back.models.rag_chunk_attribution_model import (
    RagChunkAttributionModel,
)
from sidebrain_back.models.rag_chunk_embedding_model import (
    RagChunkEmbeddingModel,
)
from sidebrain_back.models.rag_chunk_model import RagChunkModel


class RagChunkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_content_hash(
        self, content_hash: str
    ) -> RagChunkModel | None:
        return await self.db.scalar(
            select(RagChunkModel).where(
                RagChunkModel.content_hash == content_hash
            )
        )

    async def get_by_chunk_id(self, chunk_id: str) -> RagChunkModel | None:
        return await self.db.get(RagChunkModel, chunk_id)

    async def create_chunk(self, **values) -> RagChunkModel:
        values.setdefault(
            "search_vector",
            func.to_tsvector("simple", values["text"]),
        )
        chunk = RagChunkModel(**values)
        self.db.add(chunk)
        await self.db.flush()
        return chunk

    async def update_chunk(
        self, chunk: RagChunkModel, **values
    ) -> RagChunkModel:
        for field, value in values.items():
            setattr(chunk, field, value)
        if "text" in values:
            chunk.search_vector = func.to_tsvector("simple", values["text"])
        await self.db.flush()
        return chunk

    async def add_attribution(self, **values) -> RagChunkAttributionModel:
        attribution = RagChunkAttributionModel(**values)
        self.db.add(attribution)
        await self.db.flush()
        return attribution

    async def update_attribution(
        self,
        attribution: RagChunkAttributionModel,
        **values,
    ) -> RagChunkAttributionModel:
        for field, value in values.items():
            setattr(attribution, field, value)
        await self.db.flush()
        return attribution

    async def delete_attributions_for_document(self, doc_id: str) -> int:
        result = await self.db.execute(
            delete(RagChunkAttributionModel).where(
                RagChunkAttributionModel.doc_id == doc_id
            )
        )
        return int(result.rowcount or 0)

    async def get_attribution(
        self,
        *,
        chunk_id: str,
        doc_id: str,
        section_path: str,
        license: str,
    ) -> RagChunkAttributionModel | None:
        return await self.db.scalar(
            select(RagChunkAttributionModel).where(
                RagChunkAttributionModel.chunk_id == chunk_id,
                RagChunkAttributionModel.doc_id == doc_id,
                RagChunkAttributionModel.section_path == section_path,
                RagChunkAttributionModel.license == license,
            )
        )

    async def list_attributions_by_chunk(
        self, chunk_id: str
    ) -> list[RagChunkAttributionModel]:
        result = await self.db.scalars(
            select(RagChunkAttributionModel)
            .where(RagChunkAttributionModel.chunk_id == chunk_id)
            .order_by(
                RagChunkAttributionModel.source_name,
                RagChunkAttributionModel.source_url,
            )
        )
        return list(result.all())

    async def list_chunks_by_document(
        self, doc_id: str
    ) -> list[RagChunkModel]:
        result = await self.db.scalars(
            select(RagChunkModel)
            .join(RagChunkAttributionModel)
            .where(RagChunkAttributionModel.doc_id == doc_id)
            .order_by(RagChunkModel.chunk_id)
            .options(
                selectinload(RagChunkModel.attributions),
                selectinload(RagChunkModel.embeddings),
            )
        )
        return list(result.unique().all())

    async def delete_attributions_missing_from_document(
        self,
        doc_id: str,
        retained_chunk_ids: Sequence[str],
    ) -> int:
        statement = delete(RagChunkAttributionModel).where(
            RagChunkAttributionModel.doc_id == doc_id
        )
        if retained_chunk_ids:
            statement = statement.where(
                RagChunkAttributionModel.chunk_id.not_in(
                    set(retained_chunk_ids)
                )
            )
        result = await self.db.execute(statement)
        return int(result.rowcount or 0)

    async def delete_orphan_chunks(self) -> int:
        has_attribution = exists(
            select(RagChunkAttributionModel.attribution_id).where(
                RagChunkAttributionModel.chunk_id == RagChunkModel.chunk_id
            )
        )
        result = await self.db.execute(
            delete(RagChunkModel).where(~has_attribution)
        )
        return int(result.rowcount or 0)

    async def search_vector_candidates(
        self,
        *,
        embedding: list[float],
        model_id: str,
        dimensions: int,
        language: str | None,
        level: str | None,
        content_type: str | None,
        limit: int,
    ) -> list[RagChunkModel]:
        distance = RagChunkEmbeddingModel.embedding.cosine_distance(embedding)
        statement = (
            select(RagChunkModel)
            .join(
                RagChunkEmbeddingModel,
                RagChunkEmbeddingModel.chunk_id == RagChunkModel.chunk_id,
            )
            .where(
                RagChunkEmbeddingModel.model_id == model_id,
                RagChunkEmbeddingModel.dimensions == dimensions,
                self._has_matching_attribution(language, level, content_type),
            )
            .order_by(distance.asc())
            .limit(limit)
        )
        result = await self.db.scalars(statement)
        return list(result.unique().all())

    async def search_text_candidates(
        self,
        *,
        query: str,
        language: str | None,
        level: str | None,
        content_type: str | None,
        limit: int,
    ) -> list[RagChunkModel]:
        tsquery = func.websearch_to_tsquery("simple", query)
        rank = func.ts_rank_cd(RagChunkModel.search_vector, tsquery)
        statement = (
            select(RagChunkModel)
            .where(
                RagChunkModel.search_vector.op("@@")(tsquery),
                self._has_matching_attribution(language, level, content_type),
            )
            .order_by(rank.desc())
            .limit(limit)
        )
        result = await self.db.scalars(statement)
        return list(result.unique().all())

    async def list_attributions_by_chunk_ids(
        self,
        *,
        chunk_ids: Sequence[str],
        language: str | None,
        level: str | None,
        content_type: str | None,
    ) -> list[RagChunkAttributionModel]:
        if not chunk_ids:
            return []
        result = await self.db.scalars(
            select(RagChunkAttributionModel)
            .where(
                RagChunkAttributionModel.chunk_id.in_(chunk_ids),
                self._attribution_filters(language, level, content_type),
            )
            .order_by(
                RagChunkAttributionModel.source_name,
                RagChunkAttributionModel.source_url,
                RagChunkAttributionModel.section_path,
            )
        )
        return list(result.all())

    @staticmethod
    def _attribution_filters(
        language: str | None,
        level: str | None,
        content_type: str | None,
    ):
        filters = []
        if language is not None:
            filters.append(RagChunkAttributionModel.language == language)
        if level is not None:
            filters.append(RagChunkAttributionModel.level == level)
        if content_type is not None:
            filters.append(
                RagChunkAttributionModel.content_type == content_type
            )
        return and_(*filters) if filters else True

    @classmethod
    def _has_matching_attribution(
        cls,
        language: str | None,
        level: str | None,
        content_type: str | None,
    ):
        return exists(
            select(RagChunkAttributionModel.attribution_id).where(
                RagChunkAttributionModel.chunk_id == RagChunkModel.chunk_id,
                cls._attribution_filters(language, level, content_type),
            )
        )

    async def get_embedding(
        self, chunk_id: str, model_id: str, dimensions: int
    ) -> RagChunkEmbeddingModel | None:
        return await self.db.get(
            RagChunkEmbeddingModel,
            (chunk_id, model_id, dimensions),
        )

    async def get_cached_embedding_by_content_hash(
        self,
        content_hash: str,
        model_id: str,
        dimensions: int,
    ) -> RagChunkEmbeddingModel | None:
        return await self.db.scalar(
            select(RagChunkEmbeddingModel)
            .join(RagChunkModel)
            .where(
                RagChunkModel.content_hash == content_hash,
                RagChunkEmbeddingModel.model_id == model_id,
                RagChunkEmbeddingModel.dimensions == dimensions,
            )
            .limit(1)
        )

    async def list_embedding_signatures(self) -> set[tuple[str, int]]:
        result = await self.db.execute(
            select(
                RagChunkEmbeddingModel.model_id,
                RagChunkEmbeddingModel.dimensions,
            ).distinct()
        )
        return {(model, dimensions) for model, dimensions in result.all()}

    async def delete_embeddings_not_matching(
        self, model_id: str, dimensions: int
    ) -> int:
        result = await self.db.execute(
            delete(RagChunkEmbeddingModel).where(
                ~and_(
                    RagChunkEmbeddingModel.model_id == model_id,
                    RagChunkEmbeddingModel.dimensions == dimensions,
                )
            )
        )
        return int(result.rowcount or 0)

    async def create_embedding(
        self,
        *,
        chunk_id: str,
        model_id: str,
        dimensions: int,
        embedding: list[float],
        tokenizer_id: str,
        chunker_version: str,
        input_tokens: int,
    ) -> RagChunkEmbeddingModel:
        if len(embedding) != dimensions:
            raise ValueError(
                "embedding dimension does not match configuration"
            )
        record = RagChunkEmbeddingModel(
            chunk_id=chunk_id,
            model_id=model_id,
            dimensions=dimensions,
            embedding=embedding,
            tokenizer_id=tokenizer_id,
            chunker_version=chunker_version,
            input_tokens=input_tokens,
            created_at=datetime.now(UTC),
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def release_read_transaction(self) -> None:
        if self.db.in_transaction():
            await self.db.rollback()

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()


def get_rag_chunk_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RagChunkRepository:
    return RagChunkRepository(db)
