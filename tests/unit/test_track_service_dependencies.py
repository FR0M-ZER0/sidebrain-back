from unittest.mock import Mock

from sidebrain_back.services.track_service import get_track_service


def test_track_service_injects_preparation_and_mentor_dependencies():
    repository = Mock()
    db = Mock()
    badge_progress = Mock()
    preparation = Mock()
    mentor_privacy = Mock()
    mentor_conversations = Mock()

    service = get_track_service(
        repository,
        db,
        badge_progress,
        preparation,
        mentor_privacy,
        mentor_conversations,
    )

    assert service.repository is repository
    assert service.db is db
    assert service.badge_progress_service is badge_progress
    assert service.step_preparation_service is preparation
    assert service.mentor_privacy_service is mentor_privacy
    assert service.mentor_conversations is mentor_conversations
