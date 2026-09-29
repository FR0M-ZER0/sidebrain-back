from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum
from sidebrain_back.models.answer_model import Answer
from sidebrain_back.models.feedback_model import Feedback
from sidebrain_back.models.lesson_file_model import LessonFile
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.lesson_repository import LessonRepository
from sidebrain_back.schemas.lesson_schema import (
    LessonCreateRequest,
    LessonUpdateRequest,
)
from sidebrain_back.services.lesson_service import LessonService


@pytest.mark.anyio
async def test_create_persists_defaults_and_allows_position_in_other_step(
    db_session,
    learning_hierarchy_factory,
    step_factory,
):
    hierarchy = await learning_hierarchy_factory()
    other_step = await step_factory(hierarchy.track)
    service = LessonService(LessonRepository(db_session), db_session)

    first = await service.create_lesson(
        hierarchy.user,
        hierarchy.step.stp_id,
        LessonCreateRequest(
            title="  Functions  ", text="  Content  ", position=2
        ),
    )
    second = await service.create_lesson(
        hierarchy.user,
        other_step.stp_id,
        LessonCreateRequest(title="Functions", text="Content", position=2),
    )
    stored = await db_session.get(Lesson, first.id)

    assert stored is not None
    assert stored.lsn_step_id == hierarchy.step.stp_id
    assert stored.lsn_title == "Functions"
    assert stored.lsn_text == "Content"
    assert stored.lsn_status is LessonStatusEnum.IDLE
    assert stored.lsn_is_deleted is False
    assert stored.lsn_deleted_at is None
    assert first.feedbacks == first.files == first.quizzes == []
    assert second.position == first.position == 2


@pytest.mark.anyio
async def test_database_constraint_reserves_soft_deleted_position(
    db_session,
    learning_hierarchy_factory,
):
    hierarchy = await learning_hierarchy_factory(lesson_deleted=True)
    repository = LessonRepository(db_session)

    with pytest.raises(IntegrityError):
        await repository.create(
            hierarchy.step.stp_id, "Replacement", "Content", position=1
        )

    await db_session.rollback()


@pytest.mark.anyio
@pytest.mark.parametrize("unavailable", ["track", "step", "ownership"])
async def test_create_conceals_unavailable_or_unowned_step(
    unavailable,
    db_session,
    learning_hierarchy_factory,
):
    hierarchy = await learning_hierarchy_factory(
        track_deleted=unavailable == "track",
        step_deleted=unavailable == "step",
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

    with pytest.raises(ProblemDetailError) as error:
        await LessonService(
            LessonRepository(db_session), db_session
        ).create_lesson(
            user,
            hierarchy.step.stp_id,
            LessonCreateRequest(title="Lesson", text="Content", position=2),
        )

    assert error.value.status_code == 404


@pytest.mark.anyio
async def test_reads_filter_deleted_items_and_order_by_position(
    db_session,
    learning_hierarchy_factory,
    lesson_factory,
    feedback_factory,
    lesson_file_factory,
    quiz_factory,
    answer_factory,
):
    hierarchy = await learning_hierarchy_factory()
    first = hierarchy.lesson
    first.lsn_position = 2
    earlier = await lesson_factory(hierarchy.step, position=1)
    await lesson_factory(hierarchy.step, position=3, deleted=True)
    active_feedback = await feedback_factory(first, hierarchy.user)
    await feedback_factory(first, hierarchy.user, deleted=True)
    active_file = await lesson_file_factory(first)
    await lesson_file_factory(first, deleted=True)
    active_quiz = await quiz_factory(first)
    await quiz_factory(first, deleted=True)
    answer = await answer_factory(active_quiz, hierarchy.user)
    service = LessonService(LessonRepository(db_session), db_session)

    listed = await service.list_lessons_by_step_id(
        hierarchy.user, hierarchy.step.stp_id, page=1, page_size=20
    )
    detail = await service.get_lesson(hierarchy.user, first.lsn_id)

    assert [item.id for item in listed.data] == [earlier.lsn_id, first.lsn_id]
    assert listed.total_items == 2
    assert [item.id for item in detail.feedbacks] == [active_feedback.fbk_id]
    assert [item.id for item in detail.files] == [active_file.lsf_id]
    assert [item.id for item in detail.quizzes] == [active_quiz.qui_id]
    assert [item.id for item in detail.quizzes[0].answers] == [answer.ans_id]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "unavailable", ["track", "step", "lesson", "ownership", "missing"]
)
async def test_reads_return_uniform_not_found_for_unavailable_hierarchy(
    unavailable,
    db_session,
    learning_hierarchy_factory,
):
    hierarchy = await learning_hierarchy_factory(
        track_deleted=unavailable == "track",
        step_deleted=unavailable == "step",
        lesson_deleted=unavailable == "lesson",
    )
    user = hierarchy.user
    lesson_id = hierarchy.lesson.lsn_id
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
    elif unavailable == "missing":
        lesson_id = uuid4()
    service = LessonService(LessonRepository(db_session), db_session)

    with pytest.raises(ProblemDetailError) as error:
        await service.get_lesson(user, lesson_id)

    assert error.value.status_code == 404


@pytest.mark.anyio
async def test_list_supports_page_beyond_total(
    db_session,
    learning_hierarchy_factory,
):
    hierarchy = await learning_hierarchy_factory()

    response = await LessonService(
        LessonRepository(db_session), db_session
    ).list_lessons_by_step_id(
        hierarchy.user, hierarchy.step.stp_id, page=5, page_size=20
    )

    assert response.data == []
    assert response.total_items == 1
    assert response.total_pages == 1


@pytest.mark.anyio
async def test_update_preserves_step_children_and_other_lesson(
    db_session,
    learning_hierarchy_factory,
    lesson_factory,
    feedback_factory,
):
    hierarchy = await learning_hierarchy_factory()
    child = await feedback_factory(hierarchy.lesson, hierarchy.user)
    other = await lesson_factory(hierarchy.step, position=3)
    original_step_id = hierarchy.lesson.lsn_step_id
    service = LessonService(LessonRepository(db_session), db_session)

    response = await service.update_lesson(
        hierarchy.user,
        hierarchy.lesson.lsn_id,
        LessonUpdateRequest(
            title="  Updated  ",
            text="  New content  ",
            status=LessonStatusEnum.DONE,
            position=2,
        ),
    )

    assert response.title == "Updated"
    assert response.text == "New content"
    assert response.status is LessonStatusEnum.DONE
    assert response.position == 2
    assert hierarchy.lesson.lsn_step_id == original_step_id
    assert [item.id for item in response.feedbacks] == [child.fbk_id]
    assert other.lsn_position == 3


@pytest.mark.anyio
async def test_update_rejects_reserved_position_atomically(
    db_session,
    learning_hierarchy_factory,
    lesson_factory,
):
    hierarchy = await learning_hierarchy_factory()
    await lesson_factory(hierarchy.step, position=2, deleted=True)
    await db_session.commit()
    service = LessonService(LessonRepository(db_session), db_session)
    original = (
        hierarchy.lesson.lsn_title,
        hierarchy.lesson.lsn_text,
        hierarchy.lesson.lsn_status,
        hierarchy.lesson.lsn_position,
    )

    with pytest.raises(ProblemDetailError) as error:
        await service.update_lesson(
            hierarchy.user,
            hierarchy.lesson.lsn_id,
            LessonUpdateRequest(
                title="Changed", text="Changed", status="done", position=2
            ),
        )

    assert error.value.status_code == 409
    await db_session.refresh(hierarchy.lesson)
    assert (
        hierarchy.lesson.lsn_title,
        hierarchy.lesson.lsn_text,
        hierarchy.lesson.lsn_status,
        hierarchy.lesson.lsn_position,
    ) == original


@pytest.mark.anyio
async def test_soft_delete_is_terminal_and_preserves_all_physical_children(
    db_session,
    learning_hierarchy_factory,
    feedback_factory,
    lesson_file_factory,
    quiz_factory,
    answer_factory,
):
    hierarchy = await learning_hierarchy_factory()
    feedback = await feedback_factory(hierarchy.lesson, hierarchy.user)
    lesson_file = await lesson_file_factory(hierarchy.lesson)
    quiz = await quiz_factory(hierarchy.lesson)
    answer = await answer_factory(quiz, hierarchy.user)
    service = LessonService(LessonRepository(db_session), db_session)
    lesson_id = hierarchy.lesson.lsn_id
    step_id = hierarchy.step.stp_id

    await service.delete_lesson(hierarchy.user, lesson_id)

    stored = await db_session.get(Lesson, lesson_id)
    assert stored is not None
    assert stored.lsn_is_deleted is True
    assert stored.lsn_deleted_at == stored.lsn_updated_at
    assert await db_session.get(Feedback, feedback.fbk_id) is not None
    assert await db_session.get(LessonFile, lesson_file.lsf_id) is not None
    assert await db_session.get(Quiz, quiz.qui_id) is not None
    assert await db_session.get(Answer, answer.ans_id) is not None
    assert (
        await db_session.scalar(
            select(Lesson).where(Lesson.lsn_id == lesson_id)
        )
        is not None
    )

    for operation in ("get", "update", "delete"):
        await db_session.refresh(hierarchy.user)
        with pytest.raises(ProblemDetailError) as error:
            if operation == "get":
                await service.get_lesson(hierarchy.user, lesson_id)
            elif operation == "update":
                await service.update_lesson(
                    hierarchy.user,
                    lesson_id,
                    LessonUpdateRequest(
                        title="Again",
                        text="Again",
                        status="idle",
                        position=1,
                    ),
                )
            else:
                await service.delete_lesson(hierarchy.user, lesson_id)
        assert error.value.status_code == 404

    await db_session.refresh(hierarchy.user)
    listed = await service.list_lessons_by_step_id(
        hierarchy.user, step_id, page=1, page_size=20
    )
    assert listed.data == []
