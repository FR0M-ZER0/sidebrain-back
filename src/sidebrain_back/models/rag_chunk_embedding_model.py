from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.constants import RAG_VECTOR_DIMENSIONS
from sidebrain_back.core.database import Base

if TYPE_CHECKING:
    from sidebrain_back.models.rag_chunk_model import RagChunkModel


class RagChunkEmbeddingModel(Base):
    __tablename__ = "rag_chunk_embedding"
    __table_args__ = (
        Index(
            "ix_rag_chunk_embedding_hnsw_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    chunk_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("rag_chunk.chunk_id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, default="text-embedding-3-small"
    )
    dimensions: Mapped[int] = mapped_column(
        Integer, primary_key=True, default=RAG_VECTOR_DIMENSIONS
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(RAG_VECTOR_DIMENSIONS), nullable=False
    )
    tokenizer_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="cl100k_base"
    )
    chunker_version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="1"
    )
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    chunk: Mapped["RagChunkModel"] = relationship(back_populates="embeddings")
