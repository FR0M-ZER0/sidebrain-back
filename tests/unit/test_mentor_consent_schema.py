import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.mentor_consent_schema import MentorConsentAccept


def test_acceptance_requires_explicit_true():
    value = MentorConsentAccept.model_validate(
        {"notice_version": "1", "accepted": True}
    )
    assert value.accepted is True


@pytest.mark.parametrize("value", [False, 1, "true", None])
def test_acceptance_rejects_non_explicit_true(value):
    with pytest.raises(ValidationError):
        MentorConsentAccept.model_validate(
            {"notice_version": "1", "accepted": value}
        )


def test_acceptance_rejects_empty_version_and_extra_fields():
    with pytest.raises(ValidationError):
        MentorConsentAccept.model_validate(
            {"notice_version": "", "accepted": True}
        )
    with pytest.raises(ValidationError):
        MentorConsentAccept.model_validate(
            {"notice_version": "1", "accepted": True, "user_id": "other"}
        )
