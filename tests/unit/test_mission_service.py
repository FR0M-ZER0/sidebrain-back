from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.mission_schema import MissionCreate, MissionUpdate
from sidebrain_back.services.mission_service import MissionService


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


def make_mission(step_id):
    return SimpleNamespace(
        msn_id=uuid4(),
        msn_step_id=step_id,
        msn_title="Complete lessons",
        msn_difficulty="medium",
        msn_xp_reward=100,
        msn_criteria="number_of_lessons_completed",
        msn_criteria_value=3,
        msn_updated_at=datetime.now(),
        mission_progresses=[],
    )


def make_user():
    return User(
        usr_id=uuid4(),
        usr_email="mission@example.com",
        usr_name="Mission User",
        usr_password_hash="hash",
    )


class Repository:
    def __init__(self, accessible=True):
        self.step = SimpleNamespace() if accessible else None
        self.mission = None

    async def get_accessible_step(self, *_args):
        return self.step

    async def create(
        self,
        step_id,
        title,
        difficulty,
        xp_reward,
        criteria,
        criteria_value,
    ):
        self.mission = make_mission(step_id)
        self.mission.msn_title = title
        self.mission.msn_difficulty = difficulty
        self.mission.msn_xp_reward = xp_reward
        self.mission.msn_criteria = criteria
        self.mission.msn_criteria_value = criteria_value
        return self.mission

    async def get(self, *_args):
        return self.mission

    async def update(self, mission, values):
        for field, value in values.items():
            setattr(mission, f"msn_{field}", value)
        return mission

    async def soft_delete(self, mission):
        mission.msn_is_deleted = True


@pytest.mark.anyio
async def test_create_update_and_delete_are_transactional():
    repository = Repository()
    session = FakeSession()
    service = MissionService(repository, session)
    user = make_user()
    step_id = uuid4()

    created = await service.create_mission(
        user,
        step_id,
        MissionCreate(
            title=" Mission ",
            difficulty="easy",
            xpReward=10,
            criteria="complete_a_step",
            criteriaValue=1,
        ),
    )
    updated = await service.update_mission(
        user, created.id, MissionUpdate(xpReward=20)
    )
    await service.delete_mission(user, created.id)

    assert created.title == "Mission"
    assert updated.xp_reward == 20
    assert repository.mission.msn_is_deleted is True
    assert session.committed is True


@pytest.mark.anyio
async def test_create_rejects_inaccessible_step_with_404_and_rollback():
    session = FakeSession()
    service = MissionService(Repository(accessible=False), session)

    with pytest.raises(ProblemDetailError) as error:
        await service.create_mission(
            make_user(),
            uuid4(),
            MissionCreate(
                title="Mission",
                difficulty="easy",
                xpReward=10,
                criteria="complete_a_step",
                criteriaValue=1,
            ),
        )

    assert error.value.status_code == 404
    assert session.rolled_back is True
