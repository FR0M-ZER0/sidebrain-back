import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from sidebrain_back.core.database import Base


class StepPreparation(Base):
    __tablename__ = "step_preparation"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="ck_step_preparation_status",
        ),
        CheckConstraint(
            "(status = 'pending' AND finished_at IS NULL) OR "
            "(status IN ('completed', 'failed') AND finished_at IS NOT NULL)",
            name="ck_step_preparation_finished_at",
        ),
        Index("ix_step_preparation_finished_at", "finished_at"),
    )

    task_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.usr_id", ondelete="CASCADE")
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("track.trk_id", ondelete="CASCADE")
    )
    source_step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("step.stp_id", ondelete="CASCADE")
    )
    target_step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("step.stp_id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
