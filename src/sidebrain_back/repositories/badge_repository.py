from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sidebrain_back.core.database import get_db
from sidebrain_back.enums.badge_criteria_enum import BadgeCriteriaEnum
from sidebrain_back.enums.badge_progress_status_enum import (
    BadgeProgressStatusEnum,
)
from sidebrain_back.enums.badge_rarity_enum import BadgeRarityEnum
from sidebrain_back.models.badge_model import Badge
from sidebrain_back.models.badge_progress_model import BadgeProgress


class BadgeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def name_exists(
        self, name: str, exclude_id: UUID | None = None
    ) -> bool:
        query = select(Badge.bdg_id).where(
            Badge.bdg_is_deleted.is_(False),
            func.lower(func.trim(Badge.bdg_name)) == name.lower(),
        )
        if exclude_id is not None:
            query = query.where(Badge.bdg_id != exclude_id)
        return await self.db.scalar(query) is not None

    async def create(
        self,
        name: str,
        description: str | None,
        rarity: BadgeRarityEnum,
        criteria: BadgeCriteriaEnum,
        criteria_value: int,
    ) -> Badge:
        badge = Badge(
            bdg_name=name,
            bdg_description=description,
            bdg_rarity=rarity,
            bdg_criteria=criteria,
            bdg_criteria_value=criteria_value,
            bdg_is_deleted=False,
            bdg_deleted_at=None,
            badge_progresses=[],
        )
        self.db.add(badge)
        await self.db.flush()
        return badge

    def _query_with_progress(self, user_id: UUID):
        return select(Badge).options(
            selectinload(
                Badge.badge_progresses.and_(
                    BadgeProgress.bpg_user_id == user_id
                )
            )
        )

    async def list(
        self,
        user_id: UUID,
        offset: int,
        limit: int,
        *,
        status: BadgeProgressStatusEnum | None = None,
        rarity: BadgeRarityEnum | None = None,
        criteria: BadgeCriteriaEnum | None = None,
        q: str | None = None,
        sort: str = "recent",
    ) -> tuple[list[Badge], int]:
        progress_status = func.coalesce(
            BadgeProgress.bpg_status, BadgeProgressStatusEnum.IDLE
        )
        activity = func.greatest(
            Badge.bdg_updated_at,
            func.coalesce(BadgeProgress.bpg_updated_at, Badge.bdg_updated_at),
        )
        filters = [Badge.bdg_is_deleted.is_(False)]
        if status is not None:
            filters.append(progress_status == status)
        if rarity is not None:
            filters.append(Badge.bdg_rarity == rarity)
        if criteria is not None:
            filters.append(Badge.bdg_criteria == criteria)
        if q is not None:
            escaped = (
                q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            pattern = f"%{escaped}%"
            filters.append(
                or_(
                    Badge.bdg_name.ilike(pattern, escape="\\"),
                    Badge.bdg_description.ilike(pattern, escape="\\"),
                )
            )
        base = (
            select(Badge)
            .outerjoin(
                BadgeProgress,
                (BadgeProgress.bpg_badge_id == Badge.bdg_id)
                & (BadgeProgress.bpg_user_id == user_id),
            )
            .where(*filters)
        )
        total = await self.db.scalar(
            select(func.count()).select_from(base.subquery())
        )
        ordering = (
            (activity.asc(), Badge.bdg_id.asc())
            if sort == "oldest"
            else (activity.desc(), Badge.bdg_id.desc())
        )
        result = await self.db.execute(
            base.options(
                selectinload(
                    Badge.badge_progresses.and_(
                        BadgeProgress.bpg_user_id == user_id
                    )
                )
            )
            .order_by(*ordering)
            .offset(offset)
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return list(result.scalars().all()), int(total or 0)

    async def get(self, badge_id: UUID, user_id: UUID) -> Badge | None:
        result = await self.db.execute(
            self._query_with_progress(user_id).where(
                Badge.bdg_id == badge_id,
                Badge.bdg_is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def update(self, badge: Badge, values: dict[str, object]) -> Badge:
        for field, value in values.items():
            setattr(badge, f"bdg_{field}", value)
        badge.bdg_updated_at = datetime.now(UTC).replace(tzinfo=None)
        await self.db.flush()
        return badge

    async def soft_delete(self, badge: Badge) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        badge.bdg_is_deleted = True
        badge.bdg_deleted_at = now
        badge.bdg_updated_at = now
        await self.db.flush()


def get_badge_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> BadgeRepository:
    return BadgeRepository(db)
