from sidebrain_back.schemas.generation_schema import GeneratedTrack


def test_initial_content_is_limited_to_first_step():
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
                        "criteria": "number_of_lessons_completed",
                        "criteria_value": 3,
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

    assert len(generated.steps[0].lessons) == 3
    assert len(generated.steps[0].missions) == 3
    assert generated.steps[1].lessons == []
    assert len(generated.steps[1].missions) == 3
