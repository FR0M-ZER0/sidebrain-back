from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.step_schema import StepCreate, StepUpdate
from sidebrain_back.services.step_service import StepService


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


def make_step(track_id):
    return SimpleNamespace(
        stp_id=uuid4(),
        stp_track_id=track_id,
        stp_level="beginner",
        stp_title="Intro",
        stp_status="idle",
        stp_updated_at=datetime.now(),
        lessons=[],
        missions=[],
    )


def make_user():
    return User(
        usr_id=uuid4(),
        usr_email="step@example.com",
        usr_name="Step User",
        usr_password_hash="hash",
    )


class Repository:
    def __init__(self, track=True):
        self.track = SimpleNamespace() if track else None
        self.step = None
        self.created_with = None

    async def get_accessible_track(self, *_args):
        return self.track

    async def create(self, track_id, level, title):
        self.created_with = (track_id, level, title)
        self.step = make_step(track_id)
        self.step.stp_level = level
        self.step.stp_title = title
        return self.step

    async def get(self, *_args):
        return self.step

    async def update(self, step, level, title):
        step.stp_level = level
        step.stp_title = title
        return step

    async def soft_delete(self, step):
        step.stp_is_deleted = True


@pytest.mark.anyio
async def test_create_uses_track_path_and_returns_empty_children():
    repository = Repository()
    session = FakeSession()
    service = StepService(repository, session)
    user = make_user()
    track_id = uuid4()

    response = await service.create_step(
        user, track_id, StepCreate(level="beginner", title="  Intro  ")
    )

    assert repository.created_with == (track_id, "beginner", "Intro")
    assert response.lessons == []
    assert response.missions == []
    assert session.committed is True


def test_step_creation_model_initializes_child_collections():
    from sidebrain_back.models.step_model import Step

    step = Step(
        stp_track_id=uuid4(),
        stp_level="beginner",
        stp_title="Intro",
        lessons=[],
        missions=[],
    )

    assert step.lessons == []
    assert step.missions == []


@pytest.mark.anyio
async def test_create_returns_404_for_inaccessible_track():
    service = StepService(Repository(track=False), FakeSession())

    with pytest.raises(ProblemDetailError) as error:
        await service.create_step(
            make_user(), uuid4(), StepCreate(level="beginner", title="Intro")
        )

    assert error.value.status_code == 404


@pytest.mark.anyio
async def test_update_and_delete_keep_service_transactional():
    repository = Repository()
    repository.step = make_step(uuid4())
    session = FakeSession()
    service = StepService(repository, session)
    user = make_user()

    response = await service.update_step(
        user,
        repository.step.stp_track_id,
        repository.step.stp_id,
        StepUpdate(level="pro", title="Advanced"),
    )
    await service.delete_step(
        user, repository.step.stp_track_id, repository.step.stp_id
    )

    assert response.title == "Advanced"
    assert repository.step.stp_is_deleted is True
    assert session.committed is True
