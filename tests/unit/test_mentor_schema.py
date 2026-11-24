from uuid import uuid4

import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.mentor_schema import (
    MentorConversationCreate,
    MentorMessageCreate,
)


def test_mentor_message_strips_spaces():
    assert MentorMessageCreate(content="  estudar  ").content == "estudar"


@pytest.mark.parametrize("content", ["", "  ", "a" * 4001])
def test_mentor_message_rejects_invalid_content(content):
    with pytest.raises(ValidationError):
        MentorMessageCreate(content=content)


def test_mentor_requests_reject_extra_fields():
    with pytest.raises(ValidationError):
        MentorConversationCreate.model_validate(
            {
                "track_id": "00000000-0000-0000-0000-000000000001",
                "user_id": "00000000-0000-0000-0000-000000000002",
            }
        )


@pytest.mark.parametrize(
    "context",
    [
        {
            "type": "lesson",
            "lesson_id": str(uuid4()),
            "quiz_id": str(uuid4()),
        },
        {"type": "quiz", "lesson_id": str(uuid4())},
        {"type": "quiz", "lesson_id": str(uuid4()), "quiz_id": "invalid"},
        {"type": "unknown", "lesson_id": str(uuid4())},
    ],
)
def test_mentor_rejects_invalid_screen_context(context):
    with pytest.raises(ValidationError):
        MentorMessageCreate(content="Ajuda", context=context)
