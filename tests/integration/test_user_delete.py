import pytest

from sidebrain_back.core.security import create_access_token
from sidebrain_back.models.track_model import Track
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.user_repository import UserRepository
from sidebrain_back.services.auth_errors import AuthenticationError
from sidebrain_back.services.auth_service import AuthService
from sidebrain_back.services.user_service import UserService


@pytest.mark.anyio
async def test_delete_is_soft_and_prevents_authentication(db_session):
    user = User(
        usr_name="Maria",
        usr_email="maria@example.com",
        usr_password_hash="hash",
        usr_is_deleted=False,
    )
    db_session.add(user)
    await db_session.flush()
    track = Track(
        trk_user_id=user.usr_id,
        trk_title="Preservada",
        trk_is_deleted=False,
    )
    db_session.add(track)
    await db_session.flush()
    repository = UserRepository(db_session)
    token = create_access_token(user.usr_id, user.usr_token_version)
    await UserService(repository, db_session, None).delete_user(user)
    assert user.usr_is_deleted is True
    assert user.usr_deleted_at is not None
    assert await db_session.get(User, user.usr_id) is user
    assert await db_session.get(Track, track.trk_id) is track
    with pytest.raises(AuthenticationError):
        service = AuthService(repository, db_session, None)
        await service.authenticate_user_token(token)
