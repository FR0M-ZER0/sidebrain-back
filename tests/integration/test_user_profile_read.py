import pytest

from sidebrain_back.core.security import create_access_token
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.ranking_repository import RankingRepository
from sidebrain_back.repositories.user_repository import UserRepository
from sidebrain_back.services.auth_errors import AuthenticationError
from sidebrain_back.services.auth_service import AuthService
from sidebrain_back.services.user_service import UserService


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


@pytest.mark.anyio
async def test_user_me_includes_xp_and_completed_missions(
    db_session,
    learning_hierarchy_factory,
    mission_factory,
    mission_progress_factory,
):
    hierarchy = await learning_hierarchy_factory()
    completed = await mission_factory(hierarchy.step, xp_reward=125)
    await mission_progress_factory(hierarchy.user, completed, status="done")
    in_progress = await mission_factory(hierarchy.step, xp_reward=500)
    await mission_progress_factory(
        hierarchy.user, in_progress, status="in_progress"
    )

    service = UserService(
        UserRepository(db_session),
        db_session,
        rate_limiter=None,
        ranking_repository=RankingRepository(db_session),
    )
    profile = await service.get_user(hierarchy.user)

    assert profile.xp == 125
    assert profile.missions_completed == 1
    assert profile.created_at == hierarchy.user.usr_created_at
