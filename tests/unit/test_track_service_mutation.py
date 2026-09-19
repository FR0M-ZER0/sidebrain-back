from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.track_repository import TrackRepository
from sidebrain_back.schemas.track_schema import TrackUpdate
from sidebrain_back.services.track_service import TrackService


def test_patch_requires_a_field_and_normalizes_title():
    with pytest.raises(ValueError):
        TrackUpdate()

    payload = TrackUpdate(title="  Python avançado  ")
    assert payload.title == "Python avançado"
    assert payload.description is None
    assert payload.model_fields_set == {"title"}


@pytest.mark.anyio
async def test_repository_mutations_preserve_omitted_description():
    repository = TrackRepository(SimpleNamespace())
    now = datetime(2026, 1, 1, tzinfo=UTC).replace(tzinfo=None)
    track = SimpleNamespace(
        trk_title="Python",
        trk_description="Inicial",
        trk_updated_at=now,
        trk_is_deleted=False,
        trk_deleted_at=None,
    )

    await repository.update(track, "Python avançado", None, False)
    assert track.trk_title == "Python avançado"
    assert track.trk_description == "Inicial"
    assert track.trk_updated_at > now

    await repository.soft_delete(track)
    assert track.trk_is_deleted is True
    assert track.trk_deleted_at is not None
    assert track.trk_updated_at == track.trk_deleted_at


class InvalidUpdateRepository:
    def __init__(self):
        self.track = SimpleNamespace(trk_id=uuid4())

    async def get(self, *_args):
        return self.track

    async def update(self, *_args):
        return self.track


class TrackingSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.anyio
async def test_update_validates_track_response_before_commit():
    session = TrackingSession()
    service = TrackService(InvalidUpdateRepository(), session)
    user = User(
        usr_id=uuid4(),
        usr_email="user@example.com",
        usr_name="User",
        usr_password_hash="hash",
    )

    with pytest.raises(ProblemDetailError):
        await service.update_track(
            user,
            uuid4(),
            TrackUpdate(title="Python avançado"),
        )

    assert session.committed is False
    assert session.rolled_back is True
