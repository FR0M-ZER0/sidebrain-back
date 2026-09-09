import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base
from sidebrain_back.enums.mission_criteria_enum import MissionCriteriaEnum
from sidebrain_back.enums.mission_difficulty_enum import MissionDifficultyEnum

if TYPE_CHECKING:
    from sidebrain_back.models.mission_progress_model import MissionProgress
    from sidebrain_back.models.step_model import Step


class Mission(Base):
    __tablename__ = "mission"

    msn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    msn_step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("step.stp_id", ondelete="CASCADE"),
        nullable=False,
    )
    msn_title: Mapped[str] = mapped_column(String(255), nullable=False)
    msn_difficulty: Mapped[MissionDifficultyEnum] = mapped_column(
        ENUM(
            MissionDifficultyEnum,
            name="mission_difficulty",
            create_type=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    msn_xp_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    msn_criteria: Mapped[MissionCriteriaEnum] = mapped_column(
        ENUM(
            MissionCriteriaEnum,
            name="mission_criteria",
            create_type=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    msn_criteria_value: Mapped[int] = mapped_column(Integer, nullable=False)
    msn_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    msn_is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    msn_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    step: Mapped["Step"] = relationship(back_populates="missions")
    mission_progresses: Mapped[list["MissionProgress"]] = relationship(
        back_populates="mission", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Mission msn_id={self.msn_id} msn_title={self.msn_title}>"
