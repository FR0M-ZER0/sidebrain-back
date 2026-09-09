import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum

if TYPE_CHECKING:
    from sidebrain_back.models.feedback_model import Feedback
    from sidebrain_back.models.lesson_file_model import LessonFile
    from sidebrain_back.models.quiz_model import Quiz
    from sidebrain_back.models.step_model import Step


class Lesson(Base):
    __tablename__ = "lesson"
    __table_args__ = (UniqueConstraint("lsn_step_id", "lsn_position"),)

    lsn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    lsn_step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("step.stp_id", ondelete="CASCADE"),
        nullable=False,
    )
    lsn_title: Mapped[str] = mapped_column(String(255), nullable=False)
    lsn_text: Mapped[str] = mapped_column(Text, nullable=False)
    lsn_status: Mapped[LessonStatusEnum] = mapped_column(
        ENUM(
            LessonStatusEnum,
            name="lesson_status",
            create_type=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=LessonStatusEnum.IDLE,
        server_default=text("'idle'"),
    )
    lsn_position: Mapped[int] = mapped_column(Integer, nullable=False)
    lsn_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    lsn_is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    lsn_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    step: Mapped["Step"] = relationship(back_populates="lessons")
    lesson_files: Mapped[list["LessonFile"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )
    quizzes: Mapped[list["Quiz"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Lesson lsn_id={self.lsn_id} lsn_title={self.lsn_title}>"
