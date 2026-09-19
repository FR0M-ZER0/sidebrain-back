from types import SimpleNamespace
from uuid import uuid4

import pytest

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.user_model import User
from sidebrain_back.services.track_service import TrackService


class FailingRepository:
    async def create(self, *_args):
        raise RuntimeError("database details must not escape")


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.anyio
async def test_create_rolls_back_and_hides_persistence_error():
    session = FakeSession()
    service = TrackService(FailingRepository(), session)
    user = User(
        usr_id=uuid4(),
        usr_email="user@example.com",
        usr_name="User",
        usr_password_hash="hash",
    )

    with pytest.raises(ProblemDetailError) as error:
        from sidebrain_back.schemas.track_schema import TrackCreate

        await service.create_track(user, TrackCreate(title=" Python "))

    assert error.value.status_code == 500
    assert "database" not in error.value.detail
    assert session.rolled_back is True


class InvalidResponseRepository:
    def __init__(self):
        self.track = SimpleNamespace(trk_id=uuid4())

    async def create(self, *_args):
        return self.track

    async def get(self, *_args):
        return self.track


@pytest.mark.anyio
async def test_create_validates_track_response_before_commit():
    session = FakeSession()
    service = TrackService(InvalidResponseRepository(), session)
    user = User(
        usr_id=uuid4(),
        usr_email="user@example.com",
        usr_name="User",
        usr_password_hash="hash",
    )

    with pytest.raises(ProblemDetailError):
        from sidebrain_back.schemas.track_schema import TrackCreate

        await service.create_track(user, TrackCreate(title="Python"))

    assert session.committed is False
    assert session.rolled_back is True
