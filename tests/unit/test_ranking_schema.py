from uuid import uuid4

import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.ranking_schema import (
    RankingEntryResponse,
    RankingListResponse,
)


def test_ranking_entry_response_valid():
    user_id = uuid4()
    entry = RankingEntryResponse(
        position=1,
        user_id=user_id,
        name="Maria Silva",
        xp=1250,
        missions_completed=12,
    )
    assert entry.position == 1
    assert entry.user_id == user_id
    assert entry.name == "Maria Silva"
    assert entry.xp == 1250
    assert entry.missions_completed == 12

    dump = entry.model_dump(by_alias=True)
    assert dump == {
        "position": 1,
        "userId": user_id,
        "name": "Maria Silva",
        "xp": 1250,
        "missionsCompleted": 12,
    }
    assert "totalUsers" not in dump
    assert "usr_email" not in dump
    assert "usr_password_hash" not in dump
    assert "mpg_score" not in dump


def test_ranking_entry_response_from_camel_case():
    user_id = uuid4()
    entry = RankingEntryResponse.model_validate(
        {
            "position": 5,
            "userId": str(user_id),
            "name": "João Souza",
            "xp": 0,
            "missionsCompleted": 0,
        }
    )
    assert entry.position == 5
    assert entry.user_id == user_id
    assert entry.name == "João Souza"
    assert entry.xp == 0
    assert entry.missions_completed == 0


@pytest.mark.parametrize(
    "invalid_data,expected_error_field",
    [
        ({"position": 0, "xp": 10, "missionsCompleted": 1}, "position"),
        ({"position": -1, "xp": 10, "missionsCompleted": 1}, "position"),
        ({"position": 1, "xp": -1, "missionsCompleted": 1}, "xp"),
        (
            {"position": 1, "xp": 10, "missionsCompleted": -1},
            "missionsCompleted",
        ),
    ],
)
def test_ranking_entry_response_constraints(
    invalid_data, expected_error_field
):
    base_data = {
        "position": 1,
        "userId": uuid4(),
        "name": "Teste",
        "xp": 100,
        "missionsCompleted": 2,
    }
    base_data.update(invalid_data)
    with pytest.raises(ValidationError) as exc_info:
        RankingEntryResponse.model_validate(base_data)
    errors = exc_info.value.errors()
    assert any(
        err["loc"][-1] in (expected_error_field, "missions_completed")
        for err in errors
    )


def test_ranking_list_response_pagination():
    user_id = uuid4()
    entry = RankingEntryResponse(
        position=1,
        user_id=user_id,
        name="Maria",
        xp=100,
        missions_completed=1,
    )
    response = RankingListResponse.build(
        data=[entry],
        page=1,
        page_size=20,
        total_items=1,
    )
    assert response.data == [entry]
    assert response.page == 1
    assert response.page_size == 20
    assert response.total_items == 1
    assert response.total_pages == 1

    dump = response.model_dump(by_alias=True)
    assert "data" in dump
    assert dump["data"][0]["userId"] == user_id
    assert dump["data"][0]["missionsCompleted"] == 1
