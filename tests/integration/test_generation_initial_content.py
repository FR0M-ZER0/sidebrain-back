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
                        "text": "Conteúdo",
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
            },
            {"position": 2, "level": "intermediate", "title": "Prática"},
        ],
    )

    assert len(generated.steps[0].lessons) == 3
    assert generated.steps[0].mission.title == "Pratique"
    assert generated.steps[1].lessons == []
