import pytest

from sidebrain_back.core.security import create_access_token
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.user_repository import UserRepository
from sidebrain_back.services.auth_errors import AuthenticationError
from sidebrain_back.services.auth_service import AuthService


@pytest.mark.anyio
async def test_real_jwt_reads_active_user_and_rejects_uuid(db_session):
    user = User(
        usr_name="Maria",
        usr_email="maria@example.com",
        usr_password_hash="hash",
        usr_is_deleted=False,
    )
    db_session.add(user)
    await db_session.flush()
    service = AuthService(UserRepository(db_session), db_session, None)
    token = create_access_token(user.usr_id, user.usr_token_version)
    assert await service.authenticate_user_token(token) is user
    with pytest.raises(AuthenticationError):
        await service.authenticate_user_token(str(user.usr_id))
