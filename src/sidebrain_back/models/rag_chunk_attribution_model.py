import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base

if TYPE_CHECKING:
    from sidebrain_back.models.rag_chunk_model import RagChunkModel
    from sidebrain_back.models.rag_document_model import RagDocumentModel


class RagChunkAttributionModel(Base):
    __tablename__ = "rag_chunk_attribution"
    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "doc_id",
            "section_path",
            "license",
            name="uq_rag_attribution_provenance",
        ),
        CheckConstraint(
            "language IN ('python', 'javascript')",
            name="ck_rag_attribution_language",
        ),
        CheckConstraint(
            "level IN ('beginner', 'intermediate', 'advanced')",
            name="ck_rag_attribution_level",
        ),
        CheckConstraint(
            "content_type IN ('concept', 'code_example', 'reference', "
            "'tutorial', 'exercise')",
            name="ck_rag_attribution_content_type",
        ),
        Index("ix_rag_attribution_language", "language"),
        Index("ix_rag_attribution_level", "level"),
        Index("ix_rag_attribution_content_type", "content_type"),
        Index(
            "ix_rag_attribution_topics_gin",
            "topics",
            postgresql_using="gin",
        ),
    )

    attribution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chunk_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("rag_chunk.chunk_id", ondelete="CASCADE"),
        nullable=False,
    )
    doc_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("rag_document.doc_id", ondelete="CASCADE"),
        nullable=False,
    )
    section_path: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    content_type: Mapped[str] = mapped_column(String(40), nullable=False)
    topics: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'")
    )
    license: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="unknown",
        server_default="unknown",
    )
    license_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_processing_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    chunk: Mapped["RagChunkModel"] = relationship(
        back_populates="attributions"
    )
    document: Mapped["RagDocumentModel"] = relationship(
        back_populates="attributions"
    )
