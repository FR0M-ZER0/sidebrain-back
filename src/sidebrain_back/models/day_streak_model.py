import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base

if TYPE_CHECKING:
    from sidebrain_back.models.user_model import User


class DayStreak(Base):
    __tablename__ = "day_streak"

    dst_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    dst_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.usr_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    dst_value: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    dst_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="day_streak")

    def __repr__(self) -> str:
        return (
            f"<DayStreak dst_user_id={self.dst_user_id} "
            f"dst_value={self.dst_value}>"
        )
