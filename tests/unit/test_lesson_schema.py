from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.enums.lesson_file_type_enum import LessonFileTypeEnum
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum
from sidebrain_back.schemas.lesson_schema import (
    LessonCreateRequest,
    LessonResponse,
    LessonUpdateRequest,
)


@pytest.mark.parametrize("schema", [LessonCreateRequest, LessonUpdateRequest])
def test_lesson_text_fields_are_trimmed_before_validation(schema):
    payload = {
        "title": f"  {'x' * 255}  ",
        "text": "  Content  ",
        "position": 1,
    }
    if schema is LessonUpdateRequest:
        payload["status"] = "in_progress"

    result = schema.model_validate(payload)

    assert result.title == "x" * 255
    assert result.text == "Content"


@pytest.mark.parametrize("schema", [LessonCreateRequest, LessonUpdateRequest])
@pytest.mark.parametrize(
    "changes",
    [
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 256},
        {"text": "   "},
        {"position": 0},
        {"position": 1.5},
        {"step_id": "attacker"},
        {"id": "attacker"},
        {"feedbacks": []},
        {"files": []},
        {"quizzes": []},
        {"updated_at": "2026-01-01T00:00:00"},
        {"is_deleted": False},
    ],
)
def test_lesson_requests_reject_invalid_or_managed_fields(schema, changes):
    payload = {
        "title": "Variables",
        "text": "Content",
        "position": 1,
    }
    if schema is LessonUpdateRequest:
        payload["status"] = "idle"
    payload.update(changes)

    with pytest.raises(ValueError):
        schema.model_validate(payload)


def test_create_accepts_only_title_text_and_position():
    request = LessonCreateRequest(
        title="Variables",
        text="Content",
        position=1,
    )

    assert request.model_dump() == {
        "title": "Variables",
        "text": "Content",
        "position": 1,
    }


@pytest.mark.parametrize("missing", ["title", "text", "status", "position"])
def test_update_requires_all_editable_fields(missing):
    payload = {
        "title": "Variables",
        "text": "Content",
        "status": "done",
        "position": 1,
    }
    payload.pop(missing)

    with pytest.raises(ValueError):
        LessonUpdateRequest.model_validate(payload)


@pytest.mark.parametrize("status", list(LessonStatusEnum))
def test_update_accepts_every_lesson_status(status):
    request = LessonUpdateRequest(
        title="Variables",
        text="Content",
        status=status,
        position=1,
    )

    assert request.status is status


def test_lesson_response_uses_public_aliases_and_default_collections():
    now = datetime.now(UTC).replace(tzinfo=None)
    lesson = SimpleNamespace(
        lsn_id=uuid4(),
        lsn_title="Variables",
        lsn_text="Content",
        lsn_status=LessonStatusEnum.IDLE,
        lsn_position=1,
        lsn_updated_at=now,
    )

    response = LessonResponse.model_validate(lesson)

    assert response.model_dump() == {
        "id": lesson.lsn_id,
        "title": "Variables",
        "text": "Content",
        "status": LessonStatusEnum.IDLE,
        "position": 1,
        "updated_at": now,
        "feedbacks": [],
        "files": [],
        "quizzes": [],
    }


def test_response_maps_child_hierarchy_without_physical_names():
    now = datetime.now(UTC).replace(tzinfo=None)
    user_id = uuid4()
    answer = SimpleNamespace(
        ans_id=uuid4(),
        ans_user_id=user_id,
        ans_text="A storage location",
        ans_rate=AnswerRateEnum.PERFECT,
        ans_created_at=now,
        ans_updated_at=now,
    )
    lesson = SimpleNamespace(
        lsn_id=uuid4(),
        lsn_title="Variables",
        lsn_text="Content",
        lsn_status=LessonStatusEnum.DONE,
        lsn_position=2,
        lsn_updated_at=now,
        feedbacks=[
            SimpleNamespace(
                fbk_id=uuid4(),
                fbk_user_id=user_id,
                fbk_text="Useful",
                fbk_created_at=now,
                fbk_updated_at=now,
            )
        ],
        lesson_files=[
            SimpleNamespace(
                lsf_id=uuid4(),
                lsf_path="/lesson.png",
                lsf_file_type=LessonFileTypeEnum.IMAGE,
                lsf_updated_at=now,
            )
        ],
        quizzes=[
            SimpleNamespace(
                qui_id=uuid4(),
                qui_question="Question",
                qui_updated_at=now,
                answers=[answer],
            )
        ],
    )

    dumped = LessonResponse.model_validate(lesson).model_dump(mode="json")

    assert dumped["files"][0]["file_type"] == "image"
    assert dumped["feedbacks"][0]["user_id"] == str(user_id)
    assert dumped["quizzes"][0]["answers"][0]["rate"] == "perfect"
    assert not any(
        key.startswith(("lsn_", "fbk_", "lsf_", "qui_", "ans_"))
        for key in dumped
    )
