import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base

if TYPE_CHECKING:
    from sidebrain_back.models.lesson_model import Lesson
    from sidebrain_back.models.user_model import User


class Feedback(Base):
    __tablename__ = "feedback"

    fbk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    fbk_lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lesson.lsn_id", ondelete="CASCADE"),
        nullable=False,
    )
    fbk_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.usr_id", ondelete="CASCADE"),
        nullable=False,
    )
    fbk_text: Mapped[str] = mapped_column(Text, nullable=False)
    fbk_created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    fbk_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    fbk_is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    fbk_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    lesson: Mapped["Lesson"] = relationship(back_populates="feedbacks")
    user: Mapped["User"] = relationship(back_populates="feedbacks")

    def __repr__(self) -> str:
        return f"<Feedback fbk_id={self.fbk_id}>"
