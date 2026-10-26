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
                        "text": "## Conceito\n\n" + "Conteúdo. " * 120,
                        "quizzes": [
                            {"question": f"**Pergunta {index}:** explique?"}
                            for index in range(1, 6)
                        ],
                    }
                    for position in range(1, 4)
                ],
                "missions": [
                    {
                        "title": "Pratique",
                        "difficulty": "easy",
                        "xp_reward": 10,
                        "criteria": "complete_a_step",
                        "criteria_value": 1,
                    }
                ]
                * 3,
            },
            {
                "position": 2,
                "level": "intermediate",
                "title": "Prática",
                "missions": [
                    {
                        "title": "Pratique",
                        "difficulty": "easy",
                        "xp_reward": 10,
                        "criteria": "complete_a_step",
                        "criteria_value": 1,
                    }
                ]
                * 3,
            },
        ],
    )

    assert [step.position for step in generated.steps] == [1, 2]
    assert [step.level.value for step in generated.steps] == [
        "beginner",
        "intermediate",
    ]
