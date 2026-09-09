import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base
from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.enums.step_status_enum import StepStatusEnum

if TYPE_CHECKING:
    from sidebrain_back.models.lesson_model import Lesson
    from sidebrain_back.models.mission_model import Mission
    from sidebrain_back.models.track_model import Track


class Step(Base):
    __tablename__ = "step"

    stp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    stp_track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("track.trk_id", ondelete="CASCADE"),
        nullable=False,
    )
    stp_level: Mapped[StepLevelEnum] = mapped_column(
        ENUM(StepLevelEnum, name="step_level", create_type=False),
        nullable=False,
    )
    stp_title: Mapped[str] = mapped_column(String(255), nullable=False)
    stp_status: Mapped[StepStatusEnum] = mapped_column(
        ENUM(StepStatusEnum, name="step_status", create_type=False),
        nullable=False,
        default=StepStatusEnum.IDLE,
        server_default=text("'idle'"),
    )
    stp_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    stp_is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    stp_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    track: Mapped["Track"] = relationship(back_populates="steps")
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="step", cascade="all, delete-orphan"
    )
    missions: Mapped[list["Mission"]] = relationship(
        back_populates="step", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Step stp_id={self.stp_id} stp_title={self.stp_title}>"
