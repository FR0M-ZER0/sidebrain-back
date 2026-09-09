import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base
from sidebrain_back.enums.mission_progress_status_enum import (
    MissionProgressStatusEnum,
)

if TYPE_CHECKING:
    from sidebrain_back.models.mission_model import Mission
    from sidebrain_back.models.user_model import User


class MissionProgress(Base):
    __tablename__ = "mission_progress"
    __table_args__ = (UniqueConstraint("mpg_user_id", "mpg_mission_id"),)

    mpg_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    mpg_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.usr_id", ondelete="CASCADE"),
        nullable=False,
    )
    mpg_mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mission.msn_id", ondelete="CASCADE"),
        nullable=False,
    )
    mpg_status: Mapped[MissionProgressStatusEnum] = mapped_column(
        ENUM(
            MissionProgressStatusEnum,
            name="mission_progress_status",
            create_type=False,
        ),
        nullable=False,
        default=MissionProgressStatusEnum.IDLE,
        server_default=text("'idle'"),
    )
    mpg_finished_in: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    mpg_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mpg_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="mission_progresses")
    mission: Mapped["Mission"] = relationship(
        back_populates="mission_progresses"
    )

    def __repr__(self) -> str:
        return (
            f"<MissionProgress mpg_id={self.mpg_id} "
            f"mpg_status={self.mpg_status}>"
        )
