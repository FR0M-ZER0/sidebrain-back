from sidebrain_back.repositories.track_repository import TrackRepository


def test_repository_exposes_hierarchy_loader():
    options = TrackRepository._hierarchy_options(None)
    assert options is not None
