from sidebrain_back.schemas.generation_schema import GeneratedTrack


def test_first_step_can_be_created_without_mission():
    generated = GeneratedTrack(
        title="Python",
        description="Fundamentos",
        steps=[{"position": 1, "level": "beginner", "title": "Base"}],
    )

    assert generated.steps[0].mission is None
