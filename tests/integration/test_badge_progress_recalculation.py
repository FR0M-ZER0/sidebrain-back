from types import SimpleNamespace

import httpx
import pytest

from sidebrain_back.core.database import get_db
from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.enums.badge_criteria_enum import BadgeCriteriaEnum
from sidebrain_back.routers.v1.auth_router import get_current_user


@pytest.mark.anyio
async def test_badge_progress_recalculation_backfills_existing_activity(
    db_session,
    learning_hierarchy_factory,
    quiz_factory,
    answer_factory,
    badge_factory,
    test_app,
):
    hierarchy = await learning_hierarchy_factory()
    quiz = await quiz_factory(hierarchy.lesson)
    await answer_factory(quiz, hierarchy.user, rate=AnswerRateEnum.PERFECT)
    await badge_factory(
        name="Acertou uma resposta",
        criteria=BadgeCriteriaEnum.RIGHT_ANSWERS,
        criteria_value=1,
    )
    user_id = hierarchy.user.usr_id
    await db_session.commit()

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        usr_id=user_id
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        updated = await client.post("/api/v1/badges/recalculate-progress")
        assert updated.status_code == 204
        badges = await client.get("/api/v1/badges")
        assert badges.status_code == 200
        item = badges.json()["data"][0]
        assert item["progress"][0]["status"] == "done"
