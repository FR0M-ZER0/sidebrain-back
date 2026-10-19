from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base

if TYPE_CHECKING:
    from sidebrain_back.models.rag_chunk_attribution_model import (
        RagChunkAttributionModel,
    )
    from sidebrain_back.models.rag_chunk_embedding_model import (
        RagChunkEmbeddingModel,
    )


class RagChunkModel(Base):
    __tablename__ = "rag_chunk"
    __table_args__ = (
        Index(
            "ix_rag_chunk_search_vector_gin",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    chunk_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    duplicate_fingerprint: Mapped[str | None] = mapped_column(
        String(16), nullable=True, index=True
    )
    duplicate_group_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    attributions: Mapped[list["RagChunkAttributionModel"]] = relationship(
        back_populates="chunk",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    embeddings: Mapped[list["RagChunkEmbeddingModel"]] = relationship(
        back_populates="chunk",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
