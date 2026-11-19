from uuid import uuid4

import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.job_update_schema import (
    AssessmentPayload,
    JobScope,
    JobSubscribe,
    StepSummaryPayload,
    TrackGenerationPayload,
)


@pytest.mark.parametrize("channel", ["track_generation", "assessment"])
def test_uuid_channels_canonicalize_valid_resource(channel):
    resource_id = str(uuid4())
    scope = JobScope(channel=channel, resource_id=f" {resource_id} ")
    assert scope.resource_id == resource_id


def test_summary_requires_track_and_step_uuid():
    track_id = uuid4()
    step_id = uuid4()
    scope = JobScope(
        channel="step_summary",
        resource_id=f"{track_id}:{step_id}",
    )
    assert scope.resource_id == f"{track_id}:{step_id}"

    with pytest.raises(ValidationError):
        JobScope(channel="step_summary", resource_id=str(step_id))


def test_subscription_rejects_unknown_type():
    with pytest.raises(ValidationError):
        JobSubscribe(
            type="listen",
            channel="step_preparation",
            resource_id="opaque-task-id",
        )


def test_preparation_rejects_blank_resource_id():
    with pytest.raises(ValidationError):
        JobScope(channel="step_preparation", resource_id="   ")


@pytest.mark.parametrize(
    ("payload", "kwargs"),
    [
        (
            TrackGenerationPayload,
            {"request_id": uuid4(), "status": "succeeded"},
        ),
        (
            AssessmentPayload,
            {"assessment_id": uuid4(), "status": "failed"},
        ),
        (
            StepSummaryPayload,
            {"step_id": uuid4(), "status": "completed"},
        ),
    ],
)
def test_payloads_enforce_terminal_result_fields(payload, kwargs):
    with pytest.raises(ValidationError):
        payload(**kwargs)
