from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base

if TYPE_CHECKING:
    from sidebrain_back.models.user_model import User


class Avatar(Base):
    __tablename__ = "avatar"

    avt_slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    avt_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avt_image_path: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    avt_is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    avt_created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="avatar",
        foreign_keys="User.usr_avatar_slug",
    )
