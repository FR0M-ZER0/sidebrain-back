from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.quiz_schema import (
    QuizCreateRequest,
    QuizUpdateRequest,
)
from sidebrain_back.services.quiz_service import QuizService


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class CreateRepository:
    def __init__(self, lesson_status: LessonStatusEnum) -> None:
        self.lesson = SimpleNamespace(lsn_status=lesson_status)
        self.created_with: tuple[UUID, str] | None = None

    async def get_accessible_lesson(self, user_id: UUID, lesson_id: UUID):
        return self.lesson

    async def create(self, lesson_id: UUID, question: str) -> Quiz:
        self.created_with = (lesson_id, question)
        return Quiz(
            qui_id=uuid4(),
            qui_lesson_id=lesson_id,
            qui_question=question,
            qui_is_deleted=False,
            qui_deleted_at=None,
        )


class MissingLessonRepository:
    async def get_accessible_lesson(self, user_id: UUID, lesson_id: UUID):
        return None


class ReadRepository:
    def __init__(self, quizzes=None, total: int = 0, quiz=None) -> None:
        self.lesson = SimpleNamespace()
        self.quizzes = quizzes or []
        self.total = total
        self.quiz = quiz
        self.list_call = None

    async def get_accessible_lesson(self, user_id: UUID, lesson_id: UUID):
        return self.lesson

    async def list_by_lesson_id(
        self,
        lesson_id: UUID,
        offset: int,
        limit: int,
    ):
        self.list_call = (lesson_id, offset, limit)
        return self.quizzes, self.total

    async def get_accessible_quiz(self, user_id: UUID, quiz_id: UUID):
        return self.quiz

    async def update(self, quiz, question: str):
        quiz.qui_question = question
        return quiz

    async def soft_delete(self, quiz):
        quiz.qui_is_deleted = True
        quiz.qui_updated_at = "same-instant"
        quiz.qui_deleted_at = quiz.qui_updated_at


class FailingRepository(CreateRepository):
    async def create(self, lesson_id: UUID, question: str) -> Quiz:
        raise RuntimeError("sensitive database details")


def make_user() -> User:
    return User(
        usr_id=uuid4(),
        usr_email="quiz@example.com",
        usr_name="Quiz User",
        usr_password_hash="hash",
    )


@pytest.mark.anyio
@pytest.mark.parametrize("status", list(LessonStatusEnum))
async def test_create_uses_path_lesson_and_accepts_every_lesson_status(status):
    repository = CreateRepository(status)
    session = FakeSession()
    service = QuizService(repository, session)
    user = make_user()
    lesson_id = uuid4()

    response = await service.create_quiz(
        user,
        lesson_id,
        QuizCreateRequest(question="  What is a variable?  "),
    )

    assert repository.created_with == (lesson_id, "What is a variable?")
    assert response.lesson_id == lesson_id
    assert response.answers == []
    assert session.committed is True


@pytest.mark.anyio
async def test_create_returns_same_not_found_for_inaccessible_hierarchy():
    session = FakeSession()
    service = QuizService(MissingLessonRepository(), session)

    with pytest.raises(ProblemDetailError) as error:
        await service.create_quiz(
            make_user(),
            uuid4(),
            QuizCreateRequest(question="Question"),
        )

    assert error.value.status_code == 404
    assert session.committed is False


@pytest.mark.anyio
async def test_create_rolls_back_and_sanitizes_unexpected_failure():
    session = FakeSession()
    service = QuizService(
        FailingRepository(LessonStatusEnum.IDLE),
        session,
    )

    with pytest.raises(ProblemDetailError) as error:
        await service.create_quiz(
            make_user(),
            uuid4(),
            QuizCreateRequest(question="Question"),
        )

    assert error.value.status_code == 500
    assert "database" not in error.value.detail
    assert session.rolled_back is True


def make_quiz():
    return SimpleNamespace(
        qui_id=uuid4(),
        qui_lesson_id=uuid4(),
        qui_question="Question",
        answers=[],
    )


@pytest.mark.anyio
async def test_list_calculates_offset_and_builds_pagination():
    quiz = make_quiz()
    repository = ReadRepository(quizzes=[quiz], total=41)
    service = QuizService(repository, FakeSession())

    response = await service.list_quizzes_by_lesson(
        make_user(),
        quiz.qui_lesson_id,
        page=3,
        page_size=20,
    )

    assert repository.list_call == (quiz.qui_lesson_id, 40, 20)
    assert response.page == 3
    assert response.total_items == 41
    assert response.total_pages == 3
    assert [item.id for item in response.data] == [quiz.qui_id]


@pytest.mark.anyio
async def test_list_supports_page_beyond_total_and_empty_collection():
    repository = ReadRepository()
    service = QuizService(repository, FakeSession())

    response = await service.list_quizzes_by_lesson(
        make_user(),
        uuid4(),
        page=9,
        page_size=20,
    )

    assert response.data == []
    assert response.total_items == 0
    assert response.total_pages == 0


@pytest.mark.anyio
async def test_list_returns_not_found_for_inaccessible_lesson():
    repository = ReadRepository()
    repository.lesson = None
    service = QuizService(repository, FakeSession())

    with pytest.raises(ProblemDetailError) as error:
        await service.list_quizzes_by_lesson(
            make_user(),
            uuid4(),
            page=1,
            page_size=20,
        )

    assert error.value.status_code == 404


@pytest.mark.anyio
async def test_get_returns_quiz_with_answers():
    quiz = make_quiz()
    repository = ReadRepository(quiz=quiz)
    service = QuizService(repository, FakeSession())

    response = await service.get_quiz(make_user(), quiz.qui_id)

    assert response.id == quiz.qui_id
    assert response.answers == []


@pytest.mark.anyio
async def test_get_returns_not_found_for_unavailable_quiz():
    service = QuizService(ReadRepository(), FakeSession())

    with pytest.raises(ProblemDetailError) as error:
        await service.get_quiz(make_user(), uuid4())

    assert error.value.status_code == 404


@pytest.mark.anyio
async def test_update_preserves_lesson_and_answers_then_commits():
    quiz = make_quiz()
    answer = SimpleNamespace(
        ans_id=uuid4(),
        ans_user_id=uuid4(),
        ans_text="Answer",
        ans_rate=AnswerRateEnum.GOOD,
    )
    quiz.answers = [answer]
    original_lesson_id = quiz.qui_lesson_id
    session = FakeSession()
    service = QuizService(ReadRepository(quiz=quiz), session)

    response = await service.update_quiz(
        make_user(),
        quiz.qui_id,
        QuizUpdateRequest(question="  Updated  "),
    )

    assert response.question == "Updated"
    assert response.lesson_id == original_lesson_id
    assert quiz.answers == [answer]
    assert session.committed is True


@pytest.mark.anyio
async def test_update_rolls_back_if_response_cannot_be_composed():
    malformed = SimpleNamespace(qui_id=uuid4(), qui_question="Question")
    session = FakeSession()
    service = QuizService(ReadRepository(quiz=malformed), session)

    with pytest.raises(ProblemDetailError) as error:
        await service.update_quiz(
            make_user(),
            malformed.qui_id,
            QuizUpdateRequest(question="Updated"),
        )

    assert error.value.status_code == 500
    assert session.committed is False
    assert session.rolled_back is True


@pytest.mark.anyio
async def test_delete_uses_one_timestamp_and_commits():
    quiz = make_quiz()
    session = FakeSession()
    service = QuizService(ReadRepository(quiz=quiz), session)

    await service.delete_quiz(make_user(), quiz.qui_id)

    assert quiz.qui_is_deleted is True
    assert quiz.qui_deleted_at == quiz.qui_updated_at
    assert session.committed is True


@pytest.mark.anyio
@pytest.mark.parametrize("operation", ["update", "delete"])
async def test_mutation_returns_not_found_for_unavailable_quiz(operation):
    service = QuizService(ReadRepository(), FakeSession())

    with pytest.raises(ProblemDetailError) as error:
        if operation == "update":
            await service.update_quiz(
                make_user(),
                uuid4(),
                QuizUpdateRequest(question="Updated"),
            )
        else:
            await service.delete_quiz(make_user(), uuid4())

    assert error.value.status_code == 404
