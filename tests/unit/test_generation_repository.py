from uuid import uuid4

import pytest

from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.mission_model import Mission
from sidebrain_back.models.quiz_model import Quiz
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
        steps=[
            {
                "position": 1,
                "level": "beginner",
                "title": "Base",
                "lessons": [
                    {
                        "position": position,
                        "title": f"Lição {position}",
                        "text": "Conteúdo. " * 50,
                        "quiz": {"question": f"Pergunta {position}"},
                    }
                    for position in range(1, 4)
                ],
                "mission": {
                    "title": "Pratique",
                    "difficulty": "easy",
                    "xp_reward": 10,
                    "criteria": "number_of_lessons_completed",
                    "criteria_value": 3,
                },
            }
        ],
    )

    track = await repository.create(user_id, request_id, generated)

    assert track.trk_icon == "🐍"
    assert track.trk_title == "Python"
    assert track.trk_description == "Fundamentos"
    assert session.added[0] is track
    assert sum(isinstance(item, Lesson) for item in session.added) == 3
    assert sum(isinstance(item, Quiz) for item in session.added) == 3
    missions = [item for item in session.added if isinstance(item, Mission)]
    assert len(missions) == 1
    assert missions[0].msn_title == "Pratique"
    assert missions[0].msn_xp_reward == 10
