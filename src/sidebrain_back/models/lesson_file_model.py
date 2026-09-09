import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base
from sidebrain_back.enums.lesson_file_type_enum import LessonFileTypeEnum

if TYPE_CHECKING:
    from sidebrain_back.models.lesson_model import Lesson


class LessonFile(Base):
    __tablename__ = "lesson_file"

    lsf_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    lsf_lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lesson.lsn_id", ondelete="CASCADE"),
        nullable=False,
    )
    lsf_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    lsf_file_type: Mapped[LessonFileTypeEnum] = mapped_column(
        ENUM(LessonFileTypeEnum, name="lesson_file_type", create_type=False),
        nullable=False,
    )
    lsf_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    lsf_is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    lsf_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    lesson: Mapped["Lesson"] = relationship(back_populates="lesson_files")

    def __repr__(self) -> str:
        return f"<LessonFile lsf_id={self.lsf_id} lsf_path={self.lsf_path}>"
