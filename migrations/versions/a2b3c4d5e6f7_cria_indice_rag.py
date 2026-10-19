"""Cria as tabelas e índices do corpus RAG."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "a2b3c4d5e6f7"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_document",
        sa.Column("doc_id", sa.String(length=64), nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("document_hash", sa.String(length=64), nullable=False),
        sa.Column("source_version", sa.String(length=255), nullable=True),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("doc_id"),
        sa.UniqueConstraint(
            "source_name",
            "canonical_url",
            name="uq_rag_document_source_canonical_url",
        ),
    )
    op.create_table(
        "rag_chunk",
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "duplicate_fingerprint", sa.String(length=16), nullable=True
        ),
        sa.Column("duplicate_group_id", sa.String(length=64), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("chunk_id"),
    )
    op.create_index(
        "ix_rag_chunk_content_hash",
        "rag_chunk",
        ["content_hash"],
        unique=False,
    )
    op.create_index(
        "ix_rag_chunk_duplicate_fingerprint",
        "rag_chunk",
        ["duplicate_fingerprint"],
        unique=False,
    )
    op.create_index(
        "ix_rag_chunk_duplicate_group_id",
        "rag_chunk",
        ["duplicate_group_id"],
        unique=False,
    )
    op.create_index(
        "ix_rag_chunk_search_vector_gin",
        "rag_chunk",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_table(
        "rag_chunk_attribution",
        sa.Column(
            "attribution_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("doc_id", sa.String(length=64), nullable=False),
        sa.Column(
            "section_path", sa.Text(), server_default="", nullable=False
        ),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("content_type", sa.String(length=40), nullable=False),
        sa.Column(
            "topics",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "license",
            sa.String(length=255),
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
        sa.Column("license_url", sa.Text(), nullable=True),
        sa.Column(
            "external_processing_allowed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "language IN ('python', 'javascript')",
            name="ck_rag_attribution_language",
        ),
        sa.CheckConstraint(
            "level IN ('beginner', 'intermediate', 'advanced')",
            name="ck_rag_attribution_level",
        ),
        sa.CheckConstraint(
            "content_type IN ('concept', 'code_example', 'reference', "
            "'tutorial', 'exercise')",
            name="ck_rag_attribution_content_type",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["rag_chunk.chunk_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["doc_id"], ["rag_document.doc_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("attribution_id"),
        sa.UniqueConstraint(
            "chunk_id",
            "doc_id",
            "section_path",
            "license",
            name="uq_rag_attribution_provenance",
        ),
    )
    op.create_index(
        "ix_rag_attribution_language",
        "rag_chunk_attribution",
        ["language"],
        unique=False,
    )
    op.create_index(
        "ix_rag_attribution_level",
        "rag_chunk_attribution",
        ["level"],
        unique=False,
    )
    op.create_index(
        "ix_rag_attribution_content_type",
        "rag_chunk_attribution",
        ["content_type"],
        unique=False,
    )
    op.create_index(
        "ix_rag_attribution_topics_gin",
        "rag_chunk_attribution",
        ["topics"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_table(
        "rag_chunk_embedding",
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("model_id", sa.String(length=100), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("tokenizer_id", sa.String(length=100), nullable=False),
        sa.Column("chunker_version", sa.String(length=50), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["rag_chunk.chunk_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("chunk_id", "model_id", "dimensions"),
    )
    op.create_index(
        "ix_rag_chunk_embedding_hnsw_cosine",
        "rag_chunk_embedding",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rag_chunk_embedding_hnsw_cosine",
        table_name="rag_chunk_embedding",
    )
    op.drop_table("rag_chunk_embedding")
    op.drop_index(
        "ix_rag_attribution_topics_gin",
        table_name="rag_chunk_attribution",
    )
    op.drop_index(
        "ix_rag_attribution_content_type",
        table_name="rag_chunk_attribution",
    )
    op.drop_index(
        "ix_rag_attribution_level",
        table_name="rag_chunk_attribution",
    )
    op.drop_index(
        "ix_rag_attribution_language",
        table_name="rag_chunk_attribution",
    )
    op.drop_table("rag_chunk_attribution")
    op.drop_index(
        "ix_rag_chunk_search_vector_gin", table_name="rag_chunk"
    )
    op.drop_index("ix_rag_chunk_duplicate_group_id", table_name="rag_chunk")
    op.drop_index(
        "ix_rag_chunk_duplicate_fingerprint", table_name="rag_chunk"
    )
    op.drop_index("ix_rag_chunk_content_hash", table_name="rag_chunk")
    op.drop_table("rag_chunk")
    op.drop_table("rag_document")
