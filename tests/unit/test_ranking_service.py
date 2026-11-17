from uuid import uuid4

import pytest

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.ranking_repository import RankedUserRow
from sidebrain_back.services.ranking_service import RankingService


class DummyRankingRepository:
    def __init__(
        self,
        count: int = 0,
        rows: list[RankedUserRow] | None = None,
        user_row: RankedUserRow | None = None,
    ):
        self._count = count
        self._rows = rows or []
        self._user_row = user_row
        self.last_offset: int | None = None
        self.last_limit: int | None = None

    async def count_ranked_users(self) -> int:
        return self._count

    async def list_rankings(
        self, offset: int, limit: int
    ) -> list[RankedUserRow]:
        self.last_offset = offset
        self.last_limit = limit
        return self._rows

    async def get_user_ranking(self, user_id) -> RankedUserRow | None:
        return self._user_row


@pytest.mark.anyio
async def test_list_rankings_success():
    user_id = uuid4()
    row = RankedUserRow(
        position=1,
        user_id=user_id,
        name="Maria",
        xp=1500,
        missions_completed=10,
    )
    repo = DummyRankingRepository(count=55, rows=[row])
    service = RankingService(repo)

    result = await service.list_rankings(page=2, page_size=20)

    assert repo.last_offset == 20
    assert repo.last_limit == 20
    assert result.page == 2
    assert result.page_size == 20
    assert result.total_items == 55
    assert result.total_pages == 3
    assert len(result.data) == 1
    assert result.data[0].position == 1
    assert result.data[0].user_id == user_id
    assert result.data[0].name == "Maria"
    assert result.data[0].xp == 1500
    assert result.data[0].missions_completed == 10


@pytest.mark.anyio
async def test_get_my_ranking_success():
    user_id = uuid4()
    row = RankedUserRow(
        position=3,
        user_id=user_id,
        name="Carlos",
        xp=300,
        missions_completed=3,
    )
    repo = DummyRankingRepository(user_row=row)
    service = RankingService(repo)

    current_user = User(usr_id=user_id, usr_name="Carlos")
    result = await service.get_my_ranking(current_user)

    assert result.position == 3
    assert result.user_id == user_id
    assert result.name == "Carlos"
    assert result.xp == 300
    assert result.missions_completed == 3


@pytest.mark.anyio
async def test_get_my_ranking_not_found():
    repo = DummyRankingRepository(user_row=None)
    service = RankingService(repo)

    current_user = User(usr_id=uuid4(), usr_name="Inativo")
    with pytest.raises(ProblemDetailError) as exc_info:
        await service.get_my_ranking(current_user)

    assert exc_info.value.status_code == 404
    assert exc_info.value.title == "Não encontrado"
    assert exc_info.value.detail == "Usuário não encontrado."
