import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from sidebrain_back.core.database import Base


class MentorGeneration(Base):
    __tablename__ = "mentor_generation"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "idempotency_key",
            name="uq_mentor_generation_idempotency",
        ),
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name="ck_mentor_generation_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_mentor_attempt_count"),
        Index(
            "uq_mentor_generation_active",
            "conversation_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'processing')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentor_conversation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentor_message.id", ondelete="CASCADE"),
        nullable=False,
    )
    retry_of_generation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentor_generation.id", ondelete="SET NULL"),
        nullable=True,
    )
    idempotency_key: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'queued'")
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    attempt_deadline: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
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


class MentorDispatch(Base):
    __tablename__ = "mentor_dispatch"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentor_generation.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    dispatched: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class MentorSendReservation(Base):
    __tablename__ = "mentor_send_reservation"
    __table_args__ = (
        UniqueConstraint("attempt_id", name="uq_mentor_reservation_attempt"),
        CheckConstraint(
            "status IN ('in_flight', 'finished')",
            name="ck_mentor_reservation_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.usr_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentor_generation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )


class MentorPrivacyBlock(Base):
    __tablename__ = "mentor_privacy_block"
    __table_args__ = (
        CheckConstraint(
            "(blocked IS FALSE AND reason IS NULL) OR "
            "(blocked IS TRUE AND reason IS NOT NULL "
            "AND reason IN ('revocation', 'deletion'))",
            name="ck_mentor_privacy_block_reason",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.usr_id", ondelete="CASCADE"),
        primary_key=True,
    )
    blocked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    reason: Mapped[str | None] = mapped_column(String(16), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
