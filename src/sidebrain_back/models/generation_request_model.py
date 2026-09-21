import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from sidebrain_back.core.database import Base
from sidebrain_back.enums.generation_status_enum import GenerationStatusEnum
from sidebrain_back.enums.step_level_enum import StepLevelEnum


class GenerationRequest(Base):
    __tablename__ = "generation_request"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.usr_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    context_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    knowledge_level: Mapped[StepLevelEnum | None] = mapped_column(
        ENUM(
            StepLevelEnum,
            name="step_level",
            create_type=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=True,
    )
    assessment_answers: Mapped[list[dict] | None] = mapped_column(
        JSON, nullable=True
    )
    status: Mapped[GenerationStatusEnum] = mapped_column(
        ENUM(
            GenerationStatusEnum,
            name="generation_status",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=GenerationStatusEnum.PENDING,
        server_default=text("'pending'"),
    )
    track_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("track.trk_id", ondelete="SET NULL"),
        nullable=True,
    )
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
