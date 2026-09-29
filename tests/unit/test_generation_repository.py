from uuid import uuid4

import pytest

from sidebrain_back.repositories.generation_repository import (
    GenerationRepository,
)
from sidebrain_back.schemas.generation_schema import GeneratedTrack


class FakeSession:
    def __init__(self):
        self.added = []

    def add(self, instance):
        self.added.append(instance)

    async def flush(self):
        pass


@pytest.mark.anyio
async def test_create_persists_generated_icon_on_track():
    session = FakeSession()
    repository = GenerationRepository(session)
    user_id = uuid4()
    request_id = uuid4()
    generated = GeneratedTrack(
        icon="🐍",
        title="Python",
        description="Fundamentos",
        steps=[{"position": 1, "level": "beginner", "title": "Base"}],
    )

    track = await repository.create(user_id, request_id, generated)

    assert track.trk_icon == "🐍"
    assert track.trk_title == "Python"
    assert track.trk_description == "Fundamentos"
    assert session.added[0] is track
