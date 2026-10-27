import pytest

from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.user_repository import UserRepository
from sidebrain_back.schemas.user_schema import UserUpdateRequest
from sidebrain_back.services.auth_errors import ConflictError
from sidebrain_back.services.user_service import UserService


@pytest.mark.anyio
async def test_profile_update_changes_only_public_profile_fields(db_session):
    owner = User(
        usr_name="Maria",
        usr_email="maria@example.com",
        usr_password_hash="hash",
        usr_is_deleted=False,
    )
    other = User(
        usr_name="Outra",
        usr_email="used@example.com",
        usr_password_hash="hash",
        usr_is_deleted=True,
    )
    db_session.add_all([owner, other])
    await db_session.flush()
    service = UserService(UserRepository(db_session), db_session, None)
    result = await service.update_user(
        owner, UserUpdateRequest(name=" Maria Nova ")
    )
    assert result.name == "Maria Nova"
    assert result.created_at == owner.usr_created_at
    assert result.xp == 0
    assert result.missions_completed == 0
    assert owner.usr_password_hash == "hash"
    with pytest.raises(ConflictError):
        await service.update_user(
            owner, UserUpdateRequest(email="USED@example.com")
        )
