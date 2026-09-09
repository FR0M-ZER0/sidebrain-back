import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base

if TYPE_CHECKING:
    from sidebrain_back.models.answer_model import Answer
    from sidebrain_back.models.lesson_model import Lesson


class Quiz(Base):
    __tablename__ = "quiz"

    qui_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    qui_lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lesson.lsn_id", ondelete="CASCADE"),
        nullable=False,
    )
    qui_question: Mapped[str] = mapped_column(Text, nullable=False)
    qui_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    qui_is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    qui_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    lesson: Mapped["Lesson"] = relationship(back_populates="quizzes")
    answers: Mapped[list["Answer"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Quiz qui_id={self.qui_id}>"
