from uuid import uuid4

from sidebrain_back.schemas.generation_schema import LearningContext
from sidebrain_back.services.generation_request_service import (
    GenerationRequestService,
)


def test_assessment_id_is_part_of_generation_request_context():
    assessment_id = uuid4()
    context = LearningContext(
        goal="Aprender Python",
        topic="Python",
        assessment_id=assessment_id,
    )

    generation_input = GenerationRequestService.build_input(
        context, uuid4(), None
    )

    assert generation_input.assessment_id == assessment_id
    assert GenerationRequestService.normalize_context(context)[
        "assessment_id"
    ] == str(assessment_id)


def test_assessment_id_changes_idempotency_fingerprint():
    first = LearningContext(
        goal="Aprender Python", topic="Python", assessment_id=uuid4()
    )
    second = LearningContext(
        goal="Aprender Python", topic="Python", assessment_id=uuid4()
    )

    assert GenerationRequestService.fingerprint(first) != (
        GenerationRequestService.fingerprint(second)
    )
