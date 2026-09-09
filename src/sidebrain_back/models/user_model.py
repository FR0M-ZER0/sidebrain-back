import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base

if TYPE_CHECKING:
    from sidebrain_back.models.answer_model import Answer
    from sidebrain_back.models.badge_progress_model import BadgeProgress
    from sidebrain_back.models.day_streak_model import DayStreak
    from sidebrain_back.models.feedback_model import Feedback
    from sidebrain_back.models.login_model import Login
    from sidebrain_back.models.mission_progress_model import MissionProgress
    from sidebrain_back.models.track_model import Track


class User(Base):
    __tablename__ = "user"

    usr_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    usr_email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    usr_name: Mapped[str] = mapped_column(String(255), nullable=False)
    usr_password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    usr_created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    usr_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    usr_is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    usr_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    tracks: Mapped[list["Track"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    answers: Mapped[list["Answer"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    mission_progresses: Mapped[list["MissionProgress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    badge_progresses: Mapped[list["BadgeProgress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    logins: Mapped[list["Login"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    day_streak: Mapped[Optional["DayStreak"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User usr_id={self.usr_id} usr_email={self.usr_email}>"
