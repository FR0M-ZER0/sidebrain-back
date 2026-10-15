"""Cria a memória determinística global para gerações."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cache_content_type = postgresql.ENUM(
        "track", "assessment", name="generation_cache_content_type",
        create_type=False,
    )
    cache_content_type.create(op.get_bind(), checkfirst=True)
    cache_status = postgresql.ENUM(
        "pending", "ready", "failed", name="generation_cache_status",
        create_type=False,
    )
    cache_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "topic_alias",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("canonical_topic", sa.String(length=255), nullable=False),
        sa.Column("alias_version", sa.String(length=32), server_default=sa.text("'v1'"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alias", name="uq_topic_alias_alias"),
    )
    op.create_table(
        "generation_cache",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("content_type", cache_content_type, nullable=False),
        sa.Column("fingerprint_version", sa.String(length=32), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("canonical_context", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("status", cache_status, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("lease_owner", sa.String(length=255), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint", "content_type", name="uq_generation_cache_fingerprint_content_type"),
    )
    op.create_index("ix_generation_cache_fingerprint", "generation_cache", ["fingerprint"])
    op.add_column("generation_request", sa.Column("source", sa.String(length=16), nullable=True))
    op.add_column("generation_request", sa.Column("cache_id", sa.UUID(), nullable=True))
    op.create_index("ix_generation_request_cache_id", "generation_request", ["cache_id"])
    op.create_foreign_key(
        "fk_generation_request_cache_id", "generation_request", "generation_cache",
        ["cache_id"], ["id"], ondelete="SET NULL",
    )
    op.add_column("knowledge_assessment", sa.Column("source", sa.String(length=16), nullable=True))
    op.execute(sa.text(
        "INSERT INTO topic_alias (id, alias, canonical_topic, alias_version, is_active) "
        "VALUES (gen_random_uuid(), 'ingles', 'lingua inglesa', 'v1', true)"
    ))


def downgrade() -> None:
    op.drop_column("knowledge_assessment", "source")
    op.drop_constraint("fk_generation_request_cache_id", "generation_request", type_="foreignkey")
    op.drop_index("ix_generation_request_cache_id", table_name="generation_request")
    op.drop_column("generation_request", "cache_id")
    op.drop_column("generation_request", "source")
    op.drop_index("ix_generation_cache_fingerprint", table_name="generation_cache")
    op.drop_table("generation_cache")
    op.drop_table("topic_alias")
    postgresql.ENUM(name="generation_cache_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="generation_cache_content_type").drop(op.get_bind(), checkfirst=True)
