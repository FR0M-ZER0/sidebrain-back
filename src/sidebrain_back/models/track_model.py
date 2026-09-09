import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base

if TYPE_CHECKING:
    from sidebrain_back.models.step_model import Step
    from sidebrain_back.models.user_model import User


class Track(Base):
    __tablename__ = "track"

    trk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    trk_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.usr_id", ondelete="CASCADE"),
        nullable=False,
    )
    trk_title: Mapped[str] = mapped_column(String(255), nullable=False)
    trk_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trk_created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    trk_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    trk_is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    trk_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="tracks")
    steps: Mapped[list["Step"]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Track trk_id={self.trk_id} trk_title={self.trk_title}>"
