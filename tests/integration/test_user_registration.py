import asyncio

import pytest
from sqlalchemy import delete, func, select

from sidebrain_back.core.database import async_session, engine
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.user_repository import UserRepository
from sidebrain_back.schemas.user_schema import UserRegisterRequest
from sidebrain_back.services.auth_errors import ConflictError
from sidebrain_back.services.auth_service import AuthService


class LimiterDouble:
    async def check(self, *_args):
        pass

    async def record_failure(self, *_args):
        pass

    async def record_success(self, *_args):
        pass


@pytest.mark.anyio
async def test_registration_persists_normalized_email_and_argon2_hash(
    db_session,
):
    service = AuthService(
        UserRepository(db_session), db_session, LimiterDouble()
    )
    response = await service.register_user(
        UserRegisterRequest(
            name=" Maria ",
            email=" MARIA@Example.com ",
            password="senha-123",
        )
    )
    user = await db_session.scalar(
        select(User).where(User.usr_id == response.user.id)
    )
    assert user.usr_email == "maria@example.com"
    assert user.usr_password_hash.startswith("$argon2id$")
    assert user.usr_password_hash != "senha-123"


@pytest.mark.anyio
async def test_deleted_account_keeps_email_reserved(db_session):
    user = User(
        usr_name="Anterior",
        usr_email="reserved@example.com",
        usr_password_hash="hash",
        usr_is_deleted=True,
    )
    db_session.add(user)
    await db_session.flush()
    service = AuthService(
        UserRepository(db_session), db_session, LimiterDouble()
    )
    with pytest.raises(ConflictError):
        await service.register_user(
            UserRegisterRequest(
                name="Nova",
                email="RESERVED@example.com",
                password="senha-123",
            )
        )
    count = await db_session.scalar(select(func.count()).select_from(User))
    assert count == 1


@pytest.mark.anyio
async def test_concurrent_registration_keeps_one_normalized_email():
    email = "concurrent-registration@example.com"

    async def register():
        async with async_session() as session:
            service = AuthService(
                UserRepository(session), session, LimiterDouble()
            )
            return await service.register_user(
                UserRegisterRequest(
                    name="Concorrente",
                    email=email,
                    password="senha-123",
                )
            )

    results = await asyncio.gather(
        register(),
        register(),
        return_exceptions=True,
    )
    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert sum(isinstance(result, ConflictError) for result in results) == 1
    async with async_session() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.usr_email == email)
        )
        assert count == 1
        await session.execute(delete(User).where(User.usr_email == email))
        await session.commit()
    await engine.dispose()
