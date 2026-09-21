from uuid import uuid4

from sidebrain_back.schemas.generation_schema import (
    GenerationFailure,
    GenerationInput,
    GenerationSuccess,
)


def test_generation_input_requires_stable_request_and_learning_context():
    payload = GenerationInput(
        request_id=uuid4(),
        user_id=uuid4(),
        goal="Aprender Python",
        topic="Python",
    )

    assert payload.knowledge_level is None
    assert payload.assessment_answers is None


def test_generation_results_are_serializable_success_or_failure():
    request_id = uuid4()
    success = GenerationSuccess(request_id=request_id, track_id=uuid4())
    failure = GenerationFailure(
        request_id=request_id, error_code="generation_validation_failed"
    )

    assert success.model_dump(mode="json")["status"] == "succeeded"
    assert failure.model_dump(mode="json")["status"] == "failed"
    assert failure.model_dump(mode="json")["error_code"]
