import pytest

from sidebrain_back.core.security import hash_password
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.user_repository import UserRepository
from sidebrain_back.schemas.auth_schema import UserLoginRequest
from sidebrain_back.services.auth_errors import AuthenticationError
from sidebrain_back.services.auth_service import AuthService


class LimiterDouble:
    def __init__(self):
        self.failures = 0

    async def check(self, *_args):
        pass

    async def record_failure(self, *_args):
        self.failures += 1

    async def record_success(self, *_args):
        self.failures = 0


@pytest.mark.anyio
async def test_login_accepts_normalized_email_and_resets_failures(db_session):
    user = User(
        usr_name="Maria",
        usr_email="maria@example.com",
        usr_password_hash=await hash_password("senha-123"),
        usr_is_deleted=False,
    )
    db_session.add(user)
    await db_session.flush()
    limiter = LimiterDouble()
    service = AuthService(UserRepository(db_session), db_session, limiter)
    with pytest.raises(AuthenticationError):
        await service.login_user(
            UserLoginRequest(
                email="MARIA@example.com", password="senha-errada"
            ),
            "origin",
        )
    assert limiter.failures == 1
    response = await service.login_user(
        UserLoginRequest(email=" MARIA@example.com ", password="senha-123"),
        "origin",
    )
    assert response.user.id == user.usr_id
    assert limiter.failures == 0
