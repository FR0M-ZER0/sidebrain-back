from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.lesson_schema import (
    LessonCreateRequest,
    LessonUpdateRequest,
)
from sidebrain_back.services.lesson_service import LessonService


class FakeSession:
    def __init__(self, commit_error: Exception | None = None) -> None:
        self.commit_error = commit_error
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        if self.commit_error:
            raise self.commit_error
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def make_user() -> User:
    return User(
        usr_id=uuid4(),
        usr_email=f"{uuid4()}@example.com",
        usr_name="Lesson User",
        usr_password_hash="hash",
    )


def make_lesson(*, position: int = 1, status=LessonStatusEnum.IDLE):
    return SimpleNamespace(
        lsn_id=uuid4(),
        lsn_step_id=uuid4(),
        lsn_title="Variables",
        lsn_text="Content",
        lsn_status=status,
        lsn_position=position,
        lsn_updated_at=datetime.now(UTC).replace(tzinfo=None),
        lsn_is_deleted=False,
        lsn_deleted_at=None,
        feedbacks=[],
        lesson_files=[],
        quizzes=[],
    )


class LessonRepositoryDouble:
    def __init__(self, *, accessible=True, lessons=None, total=0) -> None:
        self.step = SimpleNamespace(stp_id=uuid4()) if accessible else None
        self.lesson = make_lesson() if accessible else None
        self.lessons = lessons or []
        self.total = total
        self.position_taken = False
        self.created_with = None
        self.position_call = None
        self.list_call = None

    async def get_accessible_step(self, user_id: UUID, step_id: UUID):
        return self.step

    async def get(self, user_id: UUID, lesson_id: UUID):
        return self.lesson

    async def position_exists(
        self,
        step_id: UUID,
        position: int,
        exclude_lesson_id: UUID | None = None,
    ) -> bool:
        self.position_call = (step_id, position, exclude_lesson_id)
        return self.position_taken

    async def create(
        self, step_id: UUID, title: str, text: str, position: int
    ):
        self.created_with = (step_id, title, text, position)
        lesson = make_lesson(position=position)
        lesson.lsn_step_id = step_id
        lesson.lsn_title = title
        lesson.lsn_text = text
        self.lesson = lesson
        return lesson

    async def list_by_step_id(
        self, user_id: UUID, step_id: UUID, offset: int, limit: int
    ):
        self.list_call = (user_id, step_id, offset, limit)
        return self.lessons, self.total

    async def update(self, lesson, title, text, status, position):
        lesson.lsn_title = title
        lesson.lsn_text = text
        lesson.lsn_status = status
        lesson.lsn_position = position
        lesson.lsn_updated_at = datetime.now(UTC).replace(tzinfo=None)
        return lesson

    async def delete(self, lesson):
        now = datetime.now(UTC).replace(tzinfo=None)
        lesson.lsn_is_deleted = True
        lesson.lsn_updated_at = now
        lesson.lsn_deleted_at = now


@pytest.mark.anyio
async def test_create_uses_path_step_normalized_fields_and_idle_status():
    repository = LessonRepositoryDouble()
    session = FakeSession()
    service = LessonService(repository, session)
    user = make_user()
    step_id = uuid4()

    response = await service.create_lesson(
        user,
        step_id,
        LessonCreateRequest(
            title="  Variables  ", text="  Content  ", position=2
        ),
    )

    assert repository.created_with == (step_id, "Variables", "Content", 2)
    assert response.status is LessonStatusEnum.IDLE
    assert response.feedbacks == response.files == response.quizzes == []
    assert session.committed is True


@pytest.mark.anyio
async def test_create_rejects_inaccessible_step_and_rolls_back():
    session = FakeSession()
    service = LessonService(LessonRepositoryDouble(accessible=False), session)

    with pytest.raises(ProblemDetailError) as error:
        await service.create_lesson(
            make_user(),
            uuid4(),
            LessonCreateRequest(title="Variables", text="Content", position=1),
        )

    assert error.value.status_code == 404
    assert session.rolled_back is True


@pytest.mark.anyio
async def test_create_prechecks_reserved_position_and_rolls_back():
    repository = LessonRepositoryDouble()
    repository.position_taken = True
    session = FakeSession()
    service = LessonService(repository, session)

    with pytest.raises(ProblemDetailError) as error:
        await service.create_lesson(
            make_user(),
            uuid4(),
            LessonCreateRequest(title="Variables", text="Content", position=1),
        )

    assert error.value.status_code == 409
    assert repository.created_with is None
    assert session.rolled_back is True


@pytest.mark.anyio
async def test_create_maps_concurrent_unique_violation_to_conflict():
    class UniqueViolation:
        sqlstate = "23505"

    error = IntegrityError("insert", {}, UniqueViolation())
    session = FakeSession(commit_error=error)
    service = LessonService(LessonRepositoryDouble(), session)

    with pytest.raises(ProblemDetailError) as caught:
        await service.create_lesson(
            make_user(),
            uuid4(),
            LessonCreateRequest(title="Variables", text="Content", position=1),
        )

    assert caught.value.status_code == 409
    assert session.rolled_back is True


@pytest.mark.anyio
async def test_list_calculates_offset_and_pagination():
    lesson = make_lesson()
    repository = LessonRepositoryDouble(lessons=[lesson], total=41)
    service = LessonService(repository, FakeSession())
    user = make_user()
    step_id = uuid4()

    response = await service.list_lessons_by_step_id(
        user, step_id, page=3, page_size=20
    )

    assert repository.list_call == (user.usr_id, step_id, 40, 20)
    assert response.total_pages == 3
    assert response.total_items == 41
    assert [item.id for item in response.data] == [lesson.lsn_id]


@pytest.mark.anyio
async def test_list_validates_step_before_returning_empty_page():
    repository = LessonRepositoryDouble(accessible=False)
    service = LessonService(repository, FakeSession())

    with pytest.raises(ProblemDetailError) as error:
        await service.list_lessons_by_step_id(
            make_user(), uuid4(), page=9, page_size=20
        )

    assert error.value.status_code == 404
    assert repository.list_call is None


@pytest.mark.anyio
async def test_get_materializes_complete_response():
    repository = LessonRepositoryDouble()
    response = await LessonService(repository, FakeSession()).get_lesson(
        make_user(), repository.lesson.lsn_id
    )

    assert response.id == repository.lesson.lsn_id
    assert response.files == []


@pytest.mark.anyio
async def test_get_returns_uniform_not_found_for_unavailable_lesson():
    service = LessonService(
        LessonRepositoryDouble(accessible=False), FakeSession()
    )

    with pytest.raises(ProblemDetailError) as error:
        await service.get_lesson(make_user(), uuid4())

    assert error.value.status_code == 404


@pytest.mark.anyio
@pytest.mark.parametrize("status", list(LessonStatusEnum))
async def test_update_accepts_every_status_and_excludes_current_lesson(status):
    repository = LessonRepositoryDouble()
    lesson = repository.lesson
    original_step_id = lesson.lsn_step_id
    session = FakeSession()
    service = LessonService(repository, session)

    response = await service.update_lesson(
        make_user(),
        lesson.lsn_id,
        LessonUpdateRequest(
            title="  Updated  ",
            text="  New text  ",
            status=status,
            position=2,
        ),
    )

    assert repository.position_call == (original_step_id, 2, lesson.lsn_id)
    assert lesson.lsn_step_id == original_step_id
    assert response.status is status
    assert response.title == "Updated"
    assert session.committed is True


@pytest.mark.anyio
async def test_update_rejects_position_reserved_by_another_lesson():
    repository = LessonRepositoryDouble()
    repository.position_taken = True
    session = FakeSession()
    original = repository.lesson.lsn_title

    with pytest.raises(ProblemDetailError) as error:
        await LessonService(repository, session).update_lesson(
            make_user(),
            repository.lesson.lsn_id,
            LessonUpdateRequest(
                title="Updated", text="Text", status="done", position=2
            ),
        )

    assert error.value.status_code == 409
    assert repository.lesson.lsn_title == original
    assert session.rolled_back is True


@pytest.mark.anyio
async def test_delete_uses_same_timestamp_and_commits():
    repository = LessonRepositoryDouble()
    session = FakeSession()

    await LessonService(repository, session).delete_lesson(
        make_user(), repository.lesson.lsn_id
    )

    assert repository.lesson.lsn_is_deleted is True
    assert repository.lesson.lsn_deleted_at == repository.lesson.lsn_updated_at
    assert session.committed is True


@pytest.mark.anyio
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
async def test_mutations_sanitize_unexpected_failures(operation):
    repository = LessonRepositoryDouble()
    session = FakeSession(commit_error=RuntimeError("sensitive SQL"))
    service = LessonService(repository, session)

    with pytest.raises(ProblemDetailError) as error:
        if operation == "create":
            await service.create_lesson(
                make_user(),
                uuid4(),
                LessonCreateRequest(
                    title="Variables", text="Content", position=1
                ),
            )
        elif operation == "update":
            await service.update_lesson(
                make_user(),
                repository.lesson.lsn_id,
                LessonUpdateRequest(
                    title="Variables",
                    text="Content",
                    status="done",
                    position=1,
                ),
            )
        else:
            await service.delete_lesson(make_user(), repository.lesson.lsn_id)

    assert error.value.status_code == 500
    assert "SQL" not in error.value.detail
    assert session.rolled_back is True
