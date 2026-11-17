from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.rag_document_model import RagDocumentModel


class RagDocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_source_and_canonical_url(
        self, source_name: str, canonical_url: str
    ) -> RagDocumentModel | None:
        return await self.db.scalar(
            select(RagDocumentModel).where(
                RagDocumentModel.source_name == source_name,
                RagDocumentModel.canonical_url == canonical_url,
            )
        )

    async def create(self, **values) -> RagDocumentModel:
        document = RagDocumentModel(**values)
        self.db.add(document)
        await self.db.flush()
        return document

    async def update(
        self, document: RagDocumentModel, **values
    ) -> RagDocumentModel:
        for field, value in values.items():
            setattr(document, field, value)
        await self.db.flush()
        return document

    async def list_by_source(self, source_name: str) -> list[RagDocumentModel]:
        result = await self.db.scalars(
            select(RagDocumentModel)
            .where(RagDocumentModel.source_name == source_name)
            .order_by(RagDocumentModel.canonical_url)
        )
        return list(result.all())

    async def delete_missing_from_source(
        self,
        source_name: str,
        present_canonical_urls: Sequence[str],
    ) -> int:
        statement = delete(RagDocumentModel).where(
            RagDocumentModel.source_name == source_name
        )
        if present_canonical_urls:
            statement = statement.where(
                RagDocumentModel.canonical_url.not_in(
                    set(present_canonical_urls)
                )
            )
        result = await self.db.execute(statement)
        return int(result.rowcount or 0)

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()


def get_rag_document_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RagDocumentRepository:
    return RagDocumentRepository(db)
