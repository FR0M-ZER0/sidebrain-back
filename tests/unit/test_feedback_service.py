from datetime import datetime
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
    async def commit(self):
        pass

    async def rollback(self):
        pass


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
