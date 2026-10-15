import pytest

from sidebrain_back.repositories.badge_repository import BadgeRepository
from sidebrain_back.schemas.badge_schema import BadgeCreate
from sidebrain_back.services.badge_service import BadgeService


@pytest.mark.anyio
async def test_badge_create_persists_and_returns_empty_progress(
    db_session, authenticated_user
):
    db_session.add(authenticated_user)
    await db_session.flush()
    service = BadgeService(BadgeRepository(db_session), db_session)

    response = await service.create_badge(
        authenticated_user,
        BadgeCreate(
            name="  Primeira trilha  ",
            description="Conclua uma trilha.",
            rarity="common",
            criteria="tracks_completed",
            criteria_value=1,
        ),
    )

    assert response.name == "Primeira trilha"
    assert response.progress == []
    assert await BadgeRepository(db_session).name_exists("primeira trilha")
