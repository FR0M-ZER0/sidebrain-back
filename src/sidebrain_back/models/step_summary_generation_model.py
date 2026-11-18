import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from sidebrain_back.core.database import Base


class StepSummaryGeneration(Base):
    __tablename__ = "step_summary_generation"
    __table_args__ = (
        CheckConstraint("generation > 0", name="ck_step_summary_generation"),
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="ck_step_summary_generation_status",
        ),
    )

    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("step.stp_id", ondelete="CASCADE"),
        primary_key=True,
    )
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
