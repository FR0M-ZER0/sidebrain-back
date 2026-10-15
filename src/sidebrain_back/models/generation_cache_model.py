import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from sidebrain_back.core.database import Base
from sidebrain_back.enums.generation_cache_enum import (
    GenerationCacheContentTypeEnum,
    GenerationCacheStatusEnum,
)


class GenerationCache(Base):
    __tablename__ = "generation_cache"
    __table_args__ = (
        UniqueConstraint(
            "fingerprint",
            "content_type",
            name="uq_generation_cache_fingerprint_content_type",
        ),
        Index("ix_generation_cache_fingerprint", "fingerprint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[GenerationCacheContentTypeEnum] = mapped_column(
        ENUM(
            GenerationCacheContentTypeEnum,
            name="generation_cache_content_type",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    fingerprint_version: Mapped[str] = mapped_column(
        String(32), nullable=False
    )
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    canonical_context: Mapped[dict] = mapped_column(JSON, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[GenerationCacheStatusEnum] = mapped_column(
        ENUM(
            GenerationCacheStatusEnum,
            name="generation_cache_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        server_default=text("'pending'"),
    )
    lease_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    failure_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
