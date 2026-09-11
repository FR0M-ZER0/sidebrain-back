import pytest

from sidebrain_back.schemas.track_schema import TrackCreate, TrackUpdate


def test_mutation_payloads_reject_invalid_titles():
    with pytest.raises(ValueError):
        TrackCreate(title="x" * 256)
    with pytest.raises(ValueError):
        TrackUpdate(title="")
