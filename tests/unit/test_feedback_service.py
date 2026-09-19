from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.feedback_model import Feedback
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.feedback_schema import FeedbackCreate
from sidebrain_back.services.feedback_service import FeedbackService


class FakeRepository:
    def __init__(self, feedback=None, lesson_exists=True):
        self.feedback = feedback
        self.lesson_exists_value = lesson_exists
        self.created = None

    async def lesson_exists(self, _lesson_id):
        return self.lesson_exists_value

    async def create(self, lesson_id, user_id, text):
        self.created = Feedback(
            fbk_id=uuid4(),
            fbk_lesson_id=lesson_id,
            fbk_user_id=user_id,
            fbk_text=text,
            fbk_created_at=datetime.now(),
            fbk_updated_at=datetime.now(),
            fbk_is_deleted=False,
            fbk_deleted_at=None,
        )
        self.feedback = self.created
        return self.created

    async def get(self, _feedback_id):
        return self.feedback


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.anyio
async def test_create_uses_authenticated_user_and_normalized_text():
    repository = FakeRepository()
    service = FeedbackService(repository, FakeSession())
    user = User(
        usr_id=uuid4(),
        usr_email="u@example.com",
        usr_name="U",
        usr_password_hash="hash",
    )

    response = await service.create_feedback(
        user, uuid4(), FeedbackCreate(text="  texto  ")
    )

    assert repository.created.fbk_user_id == user.usr_id
    assert repository.created.fbk_text == "texto"
    assert response.author_id == user.usr_id


@pytest.mark.anyio
async def test_create_returns_not_found_for_deleted_or_missing_lesson():
    repository = FakeRepository(lesson_exists=False)
    service = FeedbackService(repository, FakeSession())
    user = User(
        usr_id=uuid4(),
        usr_email="u@example.com",
        usr_name="U",
        usr_password_hash="hash",
    )

    with pytest.raises(ProblemDetailError) as error:
        await service.create_feedback(
            user, uuid4(), FeedbackCreate(text="texto")
        )

    assert error.value.status_code == 404
    assert repository.created is None


class InvalidResponseRepository(FakeRepository):
    def __init__(self, *, operation: str):
        feedback = SimpleNamespace(
            fbk_id=uuid4(),
            fbk_user_id=uuid4(),
            fbk_text="texto",
        )
        super().__init__(feedback=feedback)
        self.operation = operation

    async def create(self, lesson_id, user_id, text):
        self.feedback.fbk_user_id = user_id
        return self.feedback

    async def update(self, feedback, text):
        feedback.fbk_text = text
        return feedback


@pytest.mark.anyio
@pytest.mark.parametrize("operation", ["create", "update"])
async def test_response_is_validated_before_feedback_commit(operation):
    repository = InvalidResponseRepository(operation=operation)
    session = FakeSession()
    service = FeedbackService(repository, session)
    user = User(
        usr_id=repository.feedback.fbk_user_id,
        usr_email="u@example.com",
        usr_name="U",
        usr_password_hash="hash",
    )

    with pytest.raises(ProblemDetailError) as error:
        if operation == "create":
            await service.create_feedback(
                user,
                uuid4(),
                FeedbackCreate(text="texto"),
            )
        else:
            from sidebrain_back.schemas.feedback_schema import FeedbackUpdate

            await service.update_feedback(
                user,
                repository.feedback.fbk_id,
                FeedbackUpdate(text="texto atualizado"),
            )

    assert error.value.status_code == 500
    assert session.committed is False
    assert session.rolled_back is True
