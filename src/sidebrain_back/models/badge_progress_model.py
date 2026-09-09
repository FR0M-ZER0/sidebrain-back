import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base
from sidebrain_back.enums.badge_progress_status_enum import (
    BadgeProgressStatusEnum,
)

if TYPE_CHECKING:
    from sidebrain_back.models.badge_model import Badge
    from sidebrain_back.models.user_model import User


class BadgeProgress(Base):
    __tablename__ = "badge_progress"
    __table_args__ = (UniqueConstraint("bpg_user_id", "bpg_badge_id"),)

    bpg_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    bpg_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.usr_id", ondelete="CASCADE"),
        nullable=False,
    )
    bpg_badge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("badge.bdg_id", ondelete="CASCADE"),
        nullable=False,
    )
    bpg_status: Mapped[BadgeProgressStatusEnum] = mapped_column(
        ENUM(
            BadgeProgressStatusEnum,
            name="badge_progress_status",
            create_type=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=BadgeProgressStatusEnum.IDLE,
        server_default=text("'idle'"),
    )
    bpg_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="badge_progresses")
    badge: Mapped["Badge"] = relationship(back_populates="badge_progresses")

    def __repr__(self) -> str:
        return (
            f"<BadgeProgress bpg_id={self.bpg_id} "
            f"bpg_status={self.bpg_status}>"
        )
