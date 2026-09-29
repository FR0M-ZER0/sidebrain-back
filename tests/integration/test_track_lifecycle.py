from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from sidebrain_back.repositories.track_repository import TrackRepository


@pytest.mark.anyio
async def test_soft_deleted_track_has_terminal_state():
    repository = TrackRepository(SimpleNamespace())
    track = SimpleNamespace(
        trk_title="Python",
        trk_description=None,
        trk_updated_at=datetime.now(UTC).replace(tzinfo=None),
        trk_is_deleted=False,
        trk_deleted_at=None,
        trk_id=uuid4(),
    )

    await repository.soft_delete(track)

    assert track.trk_is_deleted is True
    assert track.trk_deleted_at is not None
