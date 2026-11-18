import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from sidebrain_back.core.database import Base


class MentorMessage(Base):
    __tablename__ = "mentor_message"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "sequence", name="uq_mentor_message_sequence"
        ),
        UniqueConstraint("generation_id", name="uq_mentor_message_generation"),
        CheckConstraint(
            "role IN ('student', 'mentor')", name="ck_mentor_role"
        ),
        CheckConstraint("sequence > 0", name="ck_mentor_message_sequence"),
        CheckConstraint("length(trim(content)) > 0", name="ck_mentor_content"),
        CheckConstraint(
            "(role = 'student' AND generation_id IS NULL) OR "
            "(role = 'mentor' AND generation_id IS NOT NULL)",
            name="ck_mentor_message_generation_role",
        ),
        CheckConstraint(
            "role <> 'student' OR length(content) <= 4000",
            name="ck_mentor_student_content_length",
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
    generation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "mentor_generation.id",
            ondelete="CASCADE",
            use_alter=True,
            name="fk_mentor_message_generation",
        ),
        nullable=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
