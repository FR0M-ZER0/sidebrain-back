from sidebrain_back.schemas.generation_schema import (
    GeneratedTrack,
    GenerationFailure,
    GenerationInput,
    GenerationSuccess,
)


def test_public_generation_schemas_do_not_expose_rag_fields():
    assert set(GenerationInput.model_fields) == {
        "goal",
        "topic",
        "knowledge_level",
        "assessment_answers",
        "assessment_id",
        "request_id",
        "user_id",
    }
    assert set(GenerationSuccess.model_fields) == {
        "status",
        "request_id",
        "track_id",
    }
    assert set(GenerationFailure.model_fields) == {
        "status",
        "request_id",
        "error_code",
        "detail",
    }
    assert set(GeneratedTrack.model_fields) == {
        "icon",
        "title",
        "description",
        "steps",
    }
