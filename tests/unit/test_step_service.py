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
        self.summary = None
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

    async def get_summary(self, *_args):
        return self.summary

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
@pytest.mark.parametrize("summary", ["Resumo da etapa.", None])
async def test_get_step_summary_returns_persisted_summary(summary):
    repository = Repository()
    step_id = uuid4()
    repository.summary = (step_id, summary)

    response = await StepService(repository, FakeSession()).get_step_summary(
        make_user(), uuid4(), step_id
    )

    assert response.step_id == step_id
    assert response.summary == summary


@pytest.mark.anyio
async def test_get_step_summary_returns_404_for_unavailable_step():
    with pytest.raises(ProblemDetailError) as error:
        await StepService(Repository(), FakeSession()).get_step_summary(
            make_user(), uuid4(), uuid4()
        )

    assert error.value.status_code == 404


@pytest.mark.anyio
async def test_generate_step_summary_persists_and_returns_summary():
    repository = Repository()
    step_id = uuid4()
    track_id = uuid4()
    user = make_user()
    repository.summary = (step_id, None)

    class SummaryServiceSpy:
        def __init__(self):
            self.call = None

        async def generate_summary_for_step(self, user_id, requested_step_id):
            self.call = (user_id, requested_step_id)
            return "Resumo gerado."

    summary_service = SummaryServiceSpy()
    session = FakeSession()
    response = await StepService(
        repository, session, summary_service
    ).generate_step_summary(user, track_id, step_id)

    assert response.step_id == step_id
    assert response.summary == "Resumo gerado."
    assert summary_service.call == (user.usr_id, step_id)
    assert session.committed is True


@pytest.mark.anyio
async def test_generate_step_summary_returns_404_for_unavailable_step():
    with pytest.raises(ProblemDetailError) as error:
        await StepService(Repository(), FakeSession()).generate_step_summary(
            make_user(), uuid4(), uuid4()
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
