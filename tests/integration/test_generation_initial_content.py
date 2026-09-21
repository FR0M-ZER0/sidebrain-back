from sidebrain_back.schemas.generation_schema import GeneratedTrack


def test_initial_content_is_limited_to_first_step():
    generated = GeneratedTrack(
        title="Python",
        description="Fundamentos",
        steps=[
            {
                "position": 1,
                "level": "beginner",
                "title": "Base",
                "lessons": [
                    {
                        "position": 1,
                        "title": "Variáveis",
                        "text": "Conteúdo",
                        "quiz": {"question": "Pergunta"},
                    }
                ],
            },
            {"position": 2, "level": "intermediate", "title": "Prática"},
        ],
    )

    assert len(generated.steps[0].lessons) == 1
    assert generated.steps[1].lessons == []
