from sidebrain_back.schemas.generation_schema import GeneratedTrack


def test_generation_structure_keeps_ordered_levels():
    generated = GeneratedTrack(
        icon="📘",
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
                        "text": "Conteúdo",
                        "quiz": {"question": f"Pergunta {position}"},
                    }
                    for position in range(1, 4)
                ],
                "mission": {
                    "title": "Pratique",
                    "difficulty": "easy",
                    "xp_reward": 10,
                    "criteria": "complete_a_step",
                    "criteria_value": 1,
                },
            },
            {"position": 2, "level": "intermediate", "title": "Prática"},
        ],
    )

    assert [step.position for step in generated.steps] == [1, 2]
    assert [step.level.value for step in generated.steps] == [
        "beginner",
        "intermediate",
    ]
