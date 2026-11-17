from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.routers.v1.auth_router import get_current_user
from sidebrain_back.schemas.mission_schema import (
    MissionListItemResponse,
    MissionResponse,
    MissionTrackGroupResponse,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.services.mission_service import get_mission_service


class MissionServiceDouble:
    def __init__(self, *, missing=False):
        self.missing = missing

    @staticmethod
    def _mission(mission_id=None, **changes):
        values = {
            "id": mission_id or uuid4(),
            "stepId": uuid4(),
            "title": "Complete lessons",
            "difficulty": "medium",
            "xpReward": 100,
            "criteria": "number_of_lessons_completed",
            "criteriaValue": 3,
            "updatedAt": datetime.now(UTC).replace(tzinfo=None),
            "missionProgresses": [],
        }
        values.update(changes)
        return MissionResponse(**values)

    def _raise_if_missing(self):
        if self.missing:
            raise ProblemDetailError(
                404, "Não encontrado", "Missão não encontrada."
            )

    async def create_mission(self, _user, _step_id, payload):
        self._raise_if_missing()
        return self._mission(
            title=payload.title,
            difficulty=payload.difficulty,
            xpReward=payload.xp_reward,
            criteria=payload.criteria,
            criteriaValue=payload.criteria_value,
        )

    async def list_missions_by_step_id(self, _user, _step_id, page, page_size):
        self._raise_if_missing()
        return PaginatedResponse.build(
            [self._mission()], page, page_size, total_items=1
        )

    async def get_mission(self, _user, mission_id):
        self._raise_if_missing()
        return self._mission(mission_id)

    async def update_mission(self, _user, mission_id, payload):
        self._raise_if_missing()
        return self._mission(
            mission_id,
            **{
                "title": payload.title or "Updated",
                "xpReward": payload.xp_reward or 200,
            },
        )

    async def delete_mission(self, _user, _mission_id):
        self._raise_if_missing()

    async def list_missions(self, _user, params):
        item = MissionListItemResponse(
            **self._mission().model_dump(),
            step_title="Fundamentos",
            status=params.status or "idle",
            score=0,
            last_activity_at=datetime.now(UTC).replace(tzinfo=None),
        )
        return PaginatedResponse.build(
            [
                MissionTrackGroupResponse(
                    track_id=params.track_id or uuid4(),
                    track_title="Python",
                    missions=[item],
                )
            ],
            params.page,
            params.page_size,
            1,
        )


@pytest.fixture
def mission_client(test_app):
    test_app.dependency_overrides[get_mission_service] = MissionServiceDouble
    return TestClient(test_app)


def test_create_mission_returns_camel_case_contract(mission_client):
    response = mission_client.post(
        f"/api/v1/steps/{uuid4()}/missions",
        json={
            "title": " Complete lessons ",
            "difficulty": "medium",
            "xpReward": 100,
            "criteria": "number_of_lessons_completed",
            "criteriaValue": 3,
        },
    )

    assert response.status_code == 201
    assert set(response.json()) == {
        "id",
        "stepId",
        "title",
        "difficulty",
        "xpReward",
        "criteria",
        "criteriaValue",
        "updatedAt",
        "missionProgresses",
    }


def test_list_missions_uses_pagination_defaults(mission_client):
    response = mission_client.get(f"/api/v1/steps/{uuid4()}/missions")

    assert response.status_code == 200
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 20
    assert response.json()["data"][0]["missionProgresses"] == []


def test_global_missions_contract_and_filter_binding(mission_client):
    track_id = str(uuid4())
    response = mission_client.get(
        "/api/v1/missions",
        params={
            "status": "in_progress",
            "track_id": track_id,
            "page_size": 5,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert (payload["page"], payload["page_size"], payload["total_items"]) == (
        1,
        5,
        1,
    )
    group = payload["data"][0]
    assert set(group) == {"trackId", "trackTitle", "trackIcon", "missions"}
    assert group["trackId"] == track_id
    mission = group["missions"][0]
    assert mission["status"] == "in_progress"
    assert mission["stepTitle"] == "Fundamentos"
    assert "lastActivityAt" in mission
    assert "xpReward" in mission
    assert "msn_id" not in mission


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 101},
        {"status": "invalid"},
        {"difficulty": "invalid"},
        {"criteria": "invalid"},
        {"track_id": "invalid"},
        {"sort": "invalid"},
        {"q": "   "},
        {"q": "x" * 256},
        {"user_id": str(uuid4())},
    ],
)
def test_global_missions_rejects_invalid_filters(mission_client, params):
    assert (
        mission_client.get("/api/v1/missions", params=params).status_code
        == 422
    )


def test_global_missions_requires_authentication(test_app):
    test_app.dependency_overrides.pop(get_current_user)
    with TestClient(test_app) as client:
        assert client.get("/api/v1/missions").status_code == 401


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("get", f"/api/v1/missions/{uuid4()}", None),
        ("put", f"/api/v1/missions/{uuid4()}", {"xpReward": 200}),
        ("delete", f"/api/v1/missions/{uuid4()}", None),
    ],
)
def test_mission_routes_are_registered(mission_client, method, path, payload):
    if method == "put":
        response = mission_client.put(path, json=payload)
    else:
        response = getattr(mission_client, method)(path)
    assert response.status_code in {200, 204}


def test_recalculation_requires_authentication(test_app):
    test_app.dependency_overrides.pop(get_current_user)
    with TestClient(test_app) as client:
        response = client.post(
            f"/api/v1/steps/{uuid4()}/missions/recalculate-progress"
        )
    assert response.status_code == 401
