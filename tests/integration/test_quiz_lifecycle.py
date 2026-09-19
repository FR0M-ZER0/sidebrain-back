from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum
from sidebrain_back.models.answer_model import Answer
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.quiz_repository import QuizRepository
from sidebrain_back.repositories.track_repository import TrackRepository
from sidebrain_back.schemas.quiz_schema import (
    QuizCreateRequest,
    QuizUpdateRequest,
)
from sidebrain_back.services.quiz_service import QuizService


@pytest.mark.anyio
async def test_create_persists_quiz_defaults_and_public_response(
    db_session,
    learning_hierarchy_factory,
):
    hierarchy = await learning_hierarchy_factory(
        lesson_status=LessonStatusEnum.DONE
    )
    service = QuizService(QuizRepository(db_session), db_session)

    response = await service.create_quiz(
        hierarchy.user,
        hierarchy.lesson.lsn_id,
        QuizCreateRequest(question="  What is a variable?  "),
    )
    stored = await db_session.scalar(
        select(Quiz).where(Quiz.qui_id == response.id)
    )

    assert stored is not None
    assert stored.qui_lesson_id == hierarchy.lesson.lsn_id
    assert stored.qui_is_deleted is False
    assert stored.qui_deleted_at is None
    assert response.model_dump() == {
        "id": stored.qui_id,
        "lesson_id": hierarchy.lesson.lsn_id,
        "question": "What is a variable?",
        "answers": [],
    }


@pytest.mark.anyio
@pytest.mark.parametrize(
    "deleted_parent",
    ["track", "step", "lesson"],
)
async def test_create_rejects_deleted_hierarchy(
    deleted_parent,
    db_session,
    learning_hierarchy_factory,
):
    hierarchy = await learning_hierarchy_factory(
        track_deleted=deleted_parent == "track",
        step_deleted=deleted_parent == "step",
        lesson_deleted=deleted_parent == "lesson",
    )
    service = QuizService(QuizRepository(db_session), db_session)

    with pytest.raises(ProblemDetailError) as error:
        await service.create_quiz(
            hierarchy.user,
            hierarchy.lesson.lsn_id,
            QuizCreateRequest(question="Question"),
        )

    assert error.value.status_code == 404


@pytest.mark.anyio
async def test_create_rejects_lesson_owned_by_another_user(
    db_session,
    learning_hierarchy_factory,
):
    hierarchy = await learning_hierarchy_factory()
    another_user = User(
        usr_id=uuid4(),
        usr_email=f"{uuid4()}@example.com",
        usr_name="Another User",
        usr_password_hash="hash",
        usr_is_deleted=False,
    )
    db_session.add(another_user)
    await db_session.flush()
    service = QuizService(QuizRepository(db_session), db_session)

    with pytest.raises(ProblemDetailError) as error:
        await service.create_quiz(
            another_user,
            hierarchy.lesson.lsn_id,
            QuizCreateRequest(question="Question"),
        )

    assert error.value.status_code == 404


@pytest.mark.anyio
async def test_list_orders_quizzes_and_answers_with_uuid_tiebreakers(
    db_session,
    learning_hierarchy_factory,
    quiz_factory,
    answer_factory,
):
    hierarchy = await learning_hierarchy_factory()
    now = datetime.now(UTC).replace(tzinfo=None)
    low_id = UUID("00000000-0000-0000-0000-000000000001")
    high_id = UUID("00000000-0000-0000-0000-000000000002")
    newest = await quiz_factory(
        hierarchy.lesson,
        question="Newest",
        updated_at=now + timedelta(seconds=1),
    )
    tied_low = await quiz_factory(
        hierarchy.lesson,
        quiz_id=low_id,
        question="Low",
        updated_at=now,
    )
    tied_high = await quiz_factory(
        hierarchy.lesson,
        quiz_id=high_id,
        question="High",
        updated_at=now,
    )
    await quiz_factory(hierarchy.lesson, deleted=True)
    answer_high_id = UUID("00000000-0000-0000-0000-000000000012")
    answer_low_id = UUID("00000000-0000-0000-0000-000000000011")
    await answer_factory(
        newest,
        hierarchy.user,
        answer_id=answer_high_id,
        text="Second tie",
        created_at=now,
    )
    await answer_factory(
        newest,
        hierarchy.user,
        answer_id=answer_low_id,
        text="First tie",
        created_at=now,
    )
    service = QuizService(QuizRepository(db_session), db_session)

    response = await service.list_quizzes_by_lesson(
        hierarchy.user,
        hierarchy.lesson.lsn_id,
        page=1,
        page_size=20,
    )

    assert response.total_items == 3
    assert [quiz.id for quiz in response.data] == [
        newest.qui_id,
        tied_high.qui_id,
        tied_low.qui_id,
    ]
    assert [answer.id for answer in response.data[0].answers] == [
        answer_low_id,
        answer_high_id,
    ]
    assert len({answer.id for answer in response.data[0].answers}) == 2


@pytest.mark.anyio
@pytest.mark.parametrize(
    "unavailable",
    ["track", "step", "lesson", "quiz", "ownership"],
)
async def test_read_conceals_deleted_or_unowned_hierarchy(
    unavailable,
    db_session,
    learning_hierarchy_factory,
    quiz_factory,
):
    hierarchy = await learning_hierarchy_factory(
        track_deleted=unavailable == "track",
        step_deleted=unavailable == "step",
        lesson_deleted=unavailable == "lesson",
    )
    quiz = await quiz_factory(
        hierarchy.lesson,
        deleted=unavailable == "quiz",
    )
    user = hierarchy.user
    if unavailable == "ownership":
        user = User(
            usr_id=uuid4(),
            usr_email=f"{uuid4()}@example.com",
            usr_name="Other",
            usr_password_hash="hash",
            usr_is_deleted=False,
        )
        db_session.add(user)
        await db_session.flush()
    service = QuizService(QuizRepository(db_session), db_session)

    with pytest.raises(ProblemDetailError) as error:
        await service.get_quiz(user, quiz.qui_id)

    assert error.value.status_code == 404


@pytest.mark.anyio
async def test_get_returns_all_answers_regardless_of_answer_author(
    db_session,
    learning_hierarchy_factory,
    quiz_factory,
    answer_factory,
):
    hierarchy = await learning_hierarchy_factory()
    quiz = await quiz_factory(hierarchy.lesson)
    another_user = User(
        usr_id=uuid4(),
        usr_email=f"{uuid4()}@example.com",
        usr_name="Other",
        usr_password_hash="hash",
        usr_is_deleted=False,
    )
    db_session.add(another_user)
    await db_session.flush()
    own_answer = await answer_factory(quiz, hierarchy.user)
    other_answer = await answer_factory(quiz, another_user)
    service = QuizService(QuizRepository(db_session), db_session)

    response = await service.get_quiz(hierarchy.user, quiz.qui_id)

    assert {answer.id for answer in response.answers} == {
        own_answer.ans_id,
        other_answer.ans_id,
    }


@pytest.mark.anyio
async def test_update_changes_only_question_and_preserves_answers(
    db_session,
    learning_hierarchy_factory,
    quiz_factory,
    answer_factory,
):
    hierarchy = await learning_hierarchy_factory()
    quiz = await quiz_factory(hierarchy.lesson)
    answer = await answer_factory(quiz, hierarchy.user)
    lesson_id = quiz.qui_lesson_id
    service = QuizService(QuizRepository(db_session), db_session)

    response = await service.update_quiz(
        hierarchy.user,
        quiz.qui_id,
        QuizUpdateRequest(question="  Updated  "),
    )

    assert response.question == "Updated"
    assert response.lesson_id == lesson_id
    assert [item.id for item in response.answers] == [answer.ans_id]
    stored = await db_session.get(Quiz, quiz.qui_id)
    assert stored is not None
    assert stored.qui_lesson_id == lesson_id
    assert stored.qui_is_deleted is False


@pytest.mark.anyio
async def test_soft_delete_is_terminal_and_preserves_physical_rows(
    db_session,
    learning_hierarchy_factory,
    quiz_factory,
    answer_factory,
):
    hierarchy = await learning_hierarchy_factory()
    quiz = await quiz_factory(hierarchy.lesson)
    answer = await answer_factory(quiz, hierarchy.user)
    user = hierarchy.user
    user_id = user.usr_id
    quiz_id = quiz.qui_id
    lesson_id = hierarchy.lesson.lsn_id
    track_id = hierarchy.track.trk_id
    service = QuizService(QuizRepository(db_session), db_session)

    await service.delete_quiz(user, quiz_id)

    stored_quiz = await db_session.get(Quiz, quiz_id)
    stored_answer = await db_session.get(Answer, answer.ans_id)
    assert stored_quiz is not None
    assert stored_answer is not None
    assert stored_quiz.qui_is_deleted is True
    assert stored_quiz.qui_deleted_at == stored_quiz.qui_updated_at
    assert stored_answer.ans_question_id == stored_quiz.qui_id

    with pytest.raises(ProblemDetailError):
        await service.get_quiz(user, quiz_id)
    with pytest.raises(ProblemDetailError):
        await service.update_quiz(
            user,
            quiz_id,
            QuizUpdateRequest(question="Again"),
        )
    await db_session.refresh(user)
    with pytest.raises(ProblemDetailError):
        await service.delete_quiz(user, quiz_id)
    await db_session.refresh(user)

    listed = await service.list_quizzes_by_lesson(
        user,
        lesson_id,
        page=1,
        page_size=20,
    )
    track = await TrackRepository(db_session).get(
        user_id,
        track_id,
    )
    assert listed.data == []
    assert track is not None
    assert track.steps[0].lessons[0].quizzes == []
