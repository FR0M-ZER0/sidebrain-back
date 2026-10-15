from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.schemas.mission_schema import MissionResponse
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

    async def list_missions_by_step_id(
        self, _user, _step_id, page, page_size
    ):
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
