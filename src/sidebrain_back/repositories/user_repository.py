from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.user_model import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: UUID) -> User | None:
        return await self.db.scalar(
            select(User).where(
                User.usr_id == user_id,
                User.usr_is_deleted.is_(False),
            )
        )

    async def get_for_update(self, user_id: UUID) -> User | None:
        return await self.db.scalar(
            select(User)
            .where(
                User.usr_id == user_id,
                User.usr_is_deleted.is_(False),
            )
            .with_for_update()
        )

    async def get_by_email(self, email: str) -> User | None:
        return await self.db.scalar(
            select(User).where(
                func.lower(func.btrim(User.usr_email)) == email,
                User.usr_is_deleted.is_(False),
            )
        )

    async def email_exists(
        self,
        email: str,
        exclude_user_id: UUID | None = None,
    ) -> bool:
        filters = [func.lower(func.btrim(User.usr_email)) == email]
        if exclude_user_id is not None:
            filters.append(User.usr_id != exclude_user_id)
        user_id = await self.db.scalar(
            select(User.usr_id).where(*filters).limit(1)
        )
        return user_id is not None

    async def create(
        self,
        name: str,
        email: str,
        password_hash: str,
    ) -> User:
        user = User(
            usr_name=name,
            usr_email=email,
            usr_password_hash=password_hash,
            usr_token_version=0,
            usr_is_deleted=False,
            usr_deleted_at=None,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update(
        self,
        user: User,
        name: str | None,
        email: str | None,
    ) -> User:
        if name is not None:
            user.usr_name = name
        if email is not None:
            user.usr_email = email
        user.usr_updated_at = datetime.now(UTC).replace(tzinfo=None)
        await self.db.flush()
        return user

    async def update_password(
        self,
        user: User,
        password_hash: str,
    ) -> None:
        user.usr_password_hash = password_hash
        user.usr_token_version += 1
        user.usr_updated_at = datetime.now(UTC).replace(tzinfo=None)
        await self.db.flush()

    async def delete(self, user: User) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        user.usr_is_deleted = True
        user.usr_deleted_at = now
        user.usr_updated_at = now
        await self.db.flush()


def get_user_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> UserRepository:
    return UserRepository(db)
