from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.ranking_schema import (
    RankingEntryResponse,
    RankingListResponse,
)
from sidebrain_back.services.ranking_service import get_ranking_service


class RankingServiceDouble:
    def __init__(self, *, missing=False) -> None:
        self.missing = missing

    @staticmethod
    def _entry(user_id=None, position=1, xp=1000, missions_completed=5):
        return RankingEntryResponse(
            position=position,
            user_id=user_id or uuid4(),
            name="Aluno Teste",
            xp=xp,
            missions_completed=missions_completed,
        )

    async def list_rankings(
        self, page: int = 1, page_size: int = 20
    ) -> RankingListResponse:
        if page > 5:
            return PaginatedResponse.build(
                [], page=page, page_size=page_size, total_items=2
            )
        data = [
            self._entry(position=(page - 1) * page_size + 1),
            self._entry(position=(page - 1) * page_size + 2),
        ]
        return PaginatedResponse.build(
            data, page=page, page_size=page_size, total_items=2
        )

    async def get_my_ranking(self, user) -> RankingEntryResponse:
        if self.missing:
            raise ProblemDetailError(
                404, "Não encontrado", "Usuário não encontrado."
            )
        return self._entry(user_id=user.usr_id, position=3)


@pytest.fixture
def ranking_client(test_app):
    test_app.dependency_overrides[get_ranking_service] = RankingServiceDouble
    return TestClient(test_app)


def assert_public_ranking_entry(entry: dict):
    assert set(entry.keys()) == {
        "position",
        "userId",
        "name",
        "xp",
        "missionsCompleted",
    }
    assert "totalUsers" not in entry
    assert not any(key.startswith("usr_") for key in entry)
    assert not any(key.startswith("msn_") for key in entry)
    assert not any(key.startswith("mpg_") for key in entry)
    assert "email" not in entry
    assert "password_hash" not in entry


def test_list_rankings_rejects_unauthenticated():
    client = TestClient(app)
    response = client.get("/api/v1/rankings")
    assert response.status_code == 401
    assert response.json()["status"] == 401


def test_list_rankings_default_pagination_and_contract(ranking_client):
    response = ranking_client.get("/api/v1/rankings")
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total_items"] == 2
    assert body["total_pages"] == 1
    assert len(body["data"]) == 2
    for item in body["data"]:
        assert_public_ranking_entry(item)


def test_list_rankings_page_beyond_total_pages_returns_empty_data(
    ranking_client,
):
    response = ranking_client.get("/api/v1/rankings?page=10&page_size=20")
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 10
    assert body["page_size"] == 20
    assert body["data"] == []


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page_size=0",
        "page_size=101",
        "page=-1",
        "page=abc",
    ],
)
def test_list_rankings_rejects_invalid_pagination(ranking_client, query):
    response = ranking_client.get(f"/api/v1/rankings?{query}")
    assert response.status_code == 422
    assert response.json()["status"] == 422


def test_get_my_ranking_rejects_unauthenticated():
    client = TestClient(app)
    response = client.get("/api/v1/rankings/me")
    assert response.status_code == 401
    assert response.json()["status"] == 401


def test_get_my_ranking_returns_public_contract(ranking_client):
    response = ranking_client.get("/api/v1/rankings/me")
    assert response.status_code == 200
    body = response.json()
    assert_public_ranking_entry(body)
    assert body["position"] == 3


def test_get_my_ranking_returns_404_when_user_not_found(test_app):
    def get_missing_service():
        return RankingServiceDouble(missing=True)

    test_app.dependency_overrides[get_ranking_service] = get_missing_service
    client = TestClient(test_app)
    response = client.get("/api/v1/rankings/me")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == 404
    assert body["title"] == "Não encontrado"
    assert body["detail"] == "Usuário não encontrado."
