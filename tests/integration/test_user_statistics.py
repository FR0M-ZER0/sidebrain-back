from datetime import UTC, datetime, timedelta

import httpx
import pytest

from sidebrain_back.core.database import get_db
from sidebrain_back.enums.badge_progress_status_enum import (
    BadgeProgressStatusEnum,
)
from sidebrain_back.enums.mission_progress_status_enum import (
    MissionProgressStatusEnum,
)
from sidebrain_back.models.day_streak_model import DayStreak
from sidebrain_back.routers.v1.auth_router import get_current_user


@pytest.mark.anyio
async def test_user_statistics_match_profile_and_ranking(
    test_app,
    db_session,
    learning_hierarchy_factory,
    mission_factory,
    mission_progress_factory,
):
    hierarchy = await learning_hierarchy_factory()
    mission = await mission_factory(hierarchy.step, xp_reward=275)
    await mission_progress_factory(
        hierarchy.user,
        mission,
        status=MissionProgressStatusEnum.DONE,
    )

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = lambda: hierarchy.user

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://testserver",
    ) as client:
        profile = await client.get("/api/v1/users/me")
        ranking = await client.get("/api/v1/rankings/me")
        statistics = await client.get("/api/v1/users/me/statistics")

    assert profile.status_code == 200
    assert ranking.status_code == 200
    assert statistics.status_code == 200
    assert statistics.json()["xp"] == profile.json()["xp"]
    assert (
        statistics.json()["missionsCompleted"]
        == profile.json()["missionsCompleted"]
        == ranking.json()["missionsCompleted"]
    )
    assert statistics.json()["xp"] == ranking.json()["xp"]
    assert statistics.json()["position"] == ranking.json()["position"]


@pytest.mark.anyio
async def test_user_without_progress_does_not_see_another_users_statistics(
    test_app,
    db_session,
    learning_hierarchy_factory,
    user_factory,
    mission_factory,
    mission_progress_factory,
    badge_factory,
    badge_progress_factory,
):
    other_hierarchy = await learning_hierarchy_factory()
    other = other_hierarchy.user
    caller = await user_factory(name="No progress")
    mission = await mission_factory(other_hierarchy.step, xp_reward=400)
    await mission_progress_factory(
        other,
        mission,
        status=MissionProgressStatusEnum.DONE,
    )
    badge = await badge_factory()
    await badge_progress_factory(
        badge,
        other,
        status=BadgeProgressStatusEnum.DONE.value,
    )
    db_session.add(
        DayStreak(
            dst_user_id=other.usr_id,
            dst_value=12,
            dst_updated_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    await db_session.flush()

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = lambda: caller

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://testserver",
    ) as client:
        ranking = await client.get("/api/v1/rankings/me")
        statistics = await client.get("/api/v1/users/me/statistics")

    assert ranking.status_code == 200
    assert statistics.status_code == 200
    body = statistics.json()
    assert body["xp"] == 0
    assert body["missionsCompleted"] == 0
    assert body["badgesUnlocked"] == 0
    assert body["currentDayStreak"] == 0
    assert body["position"] == ranking.json()["position"]
    assert "userId" not in body
    assert "email" not in body


@pytest.mark.anyio
async def test_expired_streak_and_badge_progress_remain_unchanged(
    test_app,
    db_session,
    learning_hierarchy_factory,
    badge_factory,
    badge_progress_factory,
):
    hierarchy = await learning_hierarchy_factory()
    user = hierarchy.user
    active_done = await badge_factory(name="Active done")
    deleted_done = await badge_factory(name="Deleted done", deleted=True)
    active_in_progress = await badge_factory(
        name="Active in progress", criteria_value=100
    )
    await badge_progress_factory(
        active_done,
        user,
        status=BadgeProgressStatusEnum.DONE.value,
    )
    await badge_progress_factory(
        deleted_done,
        user,
        status=BadgeProgressStatusEnum.DONE.value,
    )
    in_progress = await badge_progress_factory(
        active_in_progress,
        user,
        status=BadgeProgressStatusEnum.IN_PROGRESS.value,
    )
    last_active = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=2)
    streak = DayStreak(
        dst_user_id=user.usr_id,
        dst_value=8,
        dst_updated_at=last_active,
    )
    db_session.add(streak)
    await db_session.flush()
    original_progress_updated_at = in_progress.bpg_updated_at
    original_streak_value = streak.dst_value
    original_streak_updated_at = streak.dst_updated_at

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = lambda: user

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/users/me/statistics")

    assert response.status_code == 200
    assert response.json()["badgesUnlocked"] == 1
    assert response.json()["currentDayStreak"] == 0
    await db_session.refresh(in_progress)
    await db_session.refresh(streak)
    assert in_progress.bpg_status == BadgeProgressStatusEnum.IN_PROGRESS
    assert in_progress.bpg_updated_at == original_progress_updated_at
    assert streak.dst_value == original_streak_value
    assert streak.dst_updated_at == original_streak_updated_at
