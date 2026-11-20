from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from sidebrain_back.schemas.user_statistics_schema import (
    UserStatisticsResponse,
)
from sidebrain_back.services.user_statistics_service import (
    get_user_statistics_service,
)


class UserStatisticsServiceDouble:
    def __init__(self) -> None:
        self.user_id = None

    async def get_user_statistics(self, user) -> UserStatisticsResponse:
        self.user_id = user.usr_id
        return UserStatisticsResponse(
            xp=1250,
            missions_completed=12,
            position=3,
            badges_unlocked=4,
            current_day_streak=7,
        )


def test_get_user_statistics_returns_exact_public_contract(test_app):
    test_app.dependency_overrides[get_user_statistics_service] = (
        UserStatisticsServiceDouble
    )
    client = TestClient(test_app)

    response = client.get("/api/v1/users/me/statistics")

    assert response.status_code == 200
    assert response.json() == {
        "xp": 1250,
        "missionsCompleted": 12,
        "position": 3,
        "badgesUnlocked": 4,
        "currentDayStreak": 7,
    }


def test_get_user_statistics_rejects_unauthenticated_request():
    response = TestClient(app).get("/api/v1/users/me/statistics")

    assert response.status_code == 401
    assert response.json()["status"] == 401


def test_get_user_statistics_ignores_user_selector_and_exposes_no_identity(
    test_app, authenticated_user
):
    service = UserStatisticsServiceDouble()
    test_app.dependency_overrides[get_user_statistics_service] = lambda: (
        service
    )
    client = TestClient(test_app)

    response = client.get(
        "/api/v1/users/me/statistics",
        params={"user_id": str(uuid4())},
    )

    assert response.status_code == 200
    assert service.user_id == authenticated_user.usr_id
    assert set(response.json()) == {
        "xp",
        "missionsCompleted",
        "position",
        "badgesUnlocked",
        "currentDayStreak",
    }
    operation = client.get("/openapi.json").json()["paths"][
        "/api/v1/users/me/statistics"
    ]["get"]
    assert operation.get("parameters", []) == []
