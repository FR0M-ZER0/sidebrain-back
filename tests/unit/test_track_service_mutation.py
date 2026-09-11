from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from sidebrain_back.repositories.track_repository import TrackRepository
from sidebrain_back.schemas.track_schema import TrackUpdate


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
