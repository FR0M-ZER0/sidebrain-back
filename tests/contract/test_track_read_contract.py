from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.schemas.track_schema import TrackResponse


def test_track_id_is_public_uuid_field():
    fields = TrackResponse.model_fields
    assert "id" in fields
    assert fields["id"].validation_alias == "trk_id"
    assert UUID("00000000-0000-0000-0000-000000000001")


def test_track_hierarchy_quiz_preserves_timestamps_and_public_identifiers():
    now = datetime.now(UTC).replace(tzinfo=None)
    lesson_id = uuid4()
    user_id = uuid4()
    track = SimpleNamespace(
        trk_id=uuid4(),
        trk_title="Python",
        trk_description=None,
        trk_created_at=now,
        trk_updated_at=now,
        steps=[
            SimpleNamespace(
                stp_id=uuid4(),
                stp_level="beginner",
                stp_title="Fundamentals",
                stp_status="idle",
                stp_updated_at=now,
                missions=[],
                lessons=[
                    SimpleNamespace(
                        lsn_id=lesson_id,
                        lsn_title="Variables",
                        lsn_text="Content",
                        lsn_status="idle",
                        lsn_position=1,
                        lsn_updated_at=now,
                        lesson_files=[],
                        feedbacks=[],
                        quizzes=[
                            SimpleNamespace(
                                qui_id=uuid4(),
                                qui_lesson_id=lesson_id,
                                qui_question="Question",
                                qui_updated_at=now,
                                answers=[
                                    SimpleNamespace(
                                        ans_id=uuid4(),
                                        ans_user_id=user_id,
                                        ans_text="Answer",
                                        ans_rate=AnswerRateEnum.GOOD,
                                        ans_created_at=now,
                                        ans_updated_at=now,
                                    )
                                ],
                            )
                        ],
                    )
                ],
            )
        ],
    )

    response = TrackResponse.model_validate(track)
    quiz = response.steps[0].lessons[0].quizzes[0]
    answer = quiz.answers[0]

    assert quiz.lesson_id == lesson_id
    assert quiz.updated_at == now
    assert answer.user_id == user_id
    assert answer.rate is AnswerRateEnum.GOOD
    assert (answer.created_at, answer.updated_at) == (now, now)
