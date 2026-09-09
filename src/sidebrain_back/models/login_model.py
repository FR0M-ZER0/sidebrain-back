import uuid
from datetime import date as date_
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base

if TYPE_CHECKING:
    from sidebrain_back.models.user_model import User


class Login(Base):
    __tablename__ = "login"
    __table_args__ = (UniqueConstraint("lgn_user_id", "lgn_date"),)

    lgn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    lgn_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.usr_id", ondelete="CASCADE"),
        nullable=False,
    )
    lgn_date: Mapped[date_] = mapped_column(Date, nullable=False)
    lgn_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="logins")

    def __repr__(self) -> str:
        return f"<Login lgn_id={self.lgn_id} lgn_date={self.lgn_date}>"
