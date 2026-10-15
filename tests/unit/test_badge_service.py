from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.badge_model import Badge
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.badge_schema import BadgeCreate, BadgeUpdate
from sidebrain_back.services.badge_service import BadgeService


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


class FakeRepository:
    def __init__(self, badge=None, duplicate=False):
        self.badge = badge
        self.duplicate = duplicate
        self.deleted = False

    async def name_exists(self, _name, exclude_id=None):
        return self.duplicate

    async def create(
        self, name, description, rarity, criteria, criteria_value
    ):
        self.badge = Badge(
            bdg_id=uuid4(),
            bdg_name=name,
            bdg_description=description,
            bdg_rarity=rarity,
            bdg_criteria=criteria,
            bdg_criteria_value=criteria_value,
            bdg_updated_at=datetime.now(),
            bdg_is_deleted=False,
            bdg_deleted_at=None,
            badge_progresses=[],
        )
        return self.badge

    async def get(self, _badge_id, _user_id):
        return self.badge

    async def update(self, badge, values):
        for key, value in values.items():
            setattr(badge, f"bdg_{key}", value)
        return badge

    async def soft_delete(self, _badge):
        self.deleted = True


@pytest.fixture
def user():
    return User(
        usr_id=uuid4(),
        usr_email="user@example.com",
        usr_name="User",
        usr_password_hash="hash",
    )


@pytest.mark.anyio
async def test_create_normalizes_name_and_returns_empty_progress(user):
    repository = FakeRepository()
    service = BadgeService(repository, FakeSession())

    response = await service.create_badge(
        user,
        BadgeCreate(
            name="  Badge  ",
            description=None,
            rarity="common",
            criteria="xp_gained",
            criteria_value=10,
        ),
    )

    assert response.name == "Badge"
    assert response.progress == []


@pytest.mark.anyio
async def test_create_rejects_active_duplicate_without_commit(user):
    repository = FakeRepository(duplicate=True)
    session = FakeSession()
    service = BadgeService(repository, session)

    with pytest.raises(ProblemDetailError) as error:
        await service.create_badge(
            user,
            BadgeCreate(
                name="Badge",
                description=None,
                rarity="common",
                criteria="xp_gained",
                criteria_value=1,
            ),
        )

    assert error.value.status_code == 409
    assert session.committed is False
    assert session.rolled_back is True


@pytest.mark.anyio
async def test_update_is_partial_and_delete_is_logical(user):
    badge = SimpleNamespace(
        bdg_id=uuid4(),
        bdg_name="Badge",
        bdg_description="old",
        bdg_rarity="common",
        bdg_criteria="xp_gained",
        bdg_criteria_value=1,
        bdg_updated_at=datetime.now(),
        badge_progresses=[],
    )
    repository = FakeRepository(badge=badge)
    session = FakeSession()
    service = BadgeService(repository, session)

    response = await service.update_badge(
        user, badge.bdg_id, BadgeUpdate(description="new")
    )
    await service.delete_badge(user, badge.bdg_id)

    assert response.description == "new"
    assert repository.deleted is True
    assert session.committed is True
