import pytest

from sidebrain_back.core.security import (
    create_access_token,
    hash_password,
)
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.user_repository import UserRepository
from sidebrain_back.schemas.auth_schema import UserLoginRequest
from sidebrain_back.schemas.user_schema import PasswordUpdateRequest
from sidebrain_back.services.auth_errors import AuthenticationError
from sidebrain_back.services.auth_service import AuthService
from sidebrain_back.services.user_service import UserService


class LimiterDouble:
    async def check(self, *_args): pass
    async def record_failure(self, *_args): pass
    async def record_success(self, *_args): pass


@pytest.mark.anyio
async def test_password_change_increments_version_and_revokes_old_token(
    db_session,
):
    user = User(
        usr_name="Maria", usr_email="maria@example.com",
        usr_password_hash=await hash_password("senha-antiga"),
        usr_is_deleted=False,
    )
    db_session.add(user)
    await db_session.flush()
    old_token = create_access_token(user.usr_id, user.usr_token_version)
    repository = UserRepository(db_session)
    await UserService(repository, db_session, LimiterDouble()).update_password(
        user,
        PasswordUpdateRequest(
            currentPassword="senha-antiga", newPassword="senha-nova"
        ),
        "origin",
    )
    assert user.usr_token_version == 1
    with pytest.raises(AuthenticationError):
        service = AuthService(repository, db_session, None)
        await service.authenticate_user_token(old_token)
    auth_service = AuthService(
        repository,
        db_session,
        LimiterDouble(),
    )
    with pytest.raises(AuthenticationError):
        await auth_service.login_user(
            UserLoginRequest(
                email="maria@example.com", password="senha-antiga"
            ),
            "origin",
        )
    response = await auth_service.login_user(
        UserLoginRequest(
            email="maria@example.com", password="senha-nova"
        ),
        "origin",
    )
    assert response.user.id == user.usr_id
