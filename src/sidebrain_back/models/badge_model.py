import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sidebrain_back.core.database import Base
from sidebrain_back.enums.badge_criteria_enum import BadgeCriteriaEnum
from sidebrain_back.enums.badge_rarity_enum import BadgeRarityEnum

if TYPE_CHECKING:
    from sidebrain_back.models.badge_progress_model import BadgeProgress


class Badge(Base):
    __tablename__ = "badge"

    bdg_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    bdg_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bdg_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    bdg_rarity: Mapped[BadgeRarityEnum] = mapped_column(
        ENUM(
            BadgeRarityEnum,
            name="badge_rarity",
            create_type=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    bdg_criteria: Mapped[BadgeCriteriaEnum] = mapped_column(
        ENUM(
            BadgeCriteriaEnum,
            name="badge_criteria",
            create_type=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    bdg_criteria_value: Mapped[int] = mapped_column(Integer, nullable=False)
    bdg_updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    bdg_is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    bdg_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    badge_progresses: Mapped[list["BadgeProgress"]] = relationship(
        back_populates="badge", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Badge bdg_id={self.bdg_id} bdg_name={self.bdg_name}>"
