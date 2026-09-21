from sidebrain_back.schemas.generation_schema import GeneratedTrack


def test_generation_structure_keeps_ordered_levels():
    generated = GeneratedTrack(
        title="Python",
        description="Fundamentos",
        steps=[
            {"position": 1, "level": "beginner", "title": "Base"},
            {"position": 2, "level": "intermediate", "title": "Prática"},
        ],
    )

    assert [step.position for step in generated.steps] == [1, 2]
    assert [step.level.value for step in generated.steps] == [
        "beginner",
        "intermediate",
    ]
