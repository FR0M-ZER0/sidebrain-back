import pytest

from sidebrain_back.models.mission_model import Mission
from sidebrain_back.repositories.mission_repository import MissionRepository
from sidebrain_back.schemas.mission_schema import MissionCreate, MissionUpdate
from sidebrain_back.services.mission_service import MissionService


@pytest.mark.anyio
async def test_mission_lifecycle_and_soft_delete(
    db_session,
    learning_hierarchy_factory,
):
    hierarchy = await learning_hierarchy_factory()
    service = MissionService(MissionRepository(db_session), db_session)

    created = await service.create_mission(
        hierarchy.user,
        hierarchy.step.stp_id,
        MissionCreate(
            title=" Complete lessons ",
            difficulty="medium",
            xpReward=100,
            criteria="number_of_lessons_completed",
            criteriaValue=3,
        ),
    )
    listed = await service.list_missions_by_step_id(
        hierarchy.user, hierarchy.step.stp_id, 1, 20
    )
    updated = await service.update_mission(
        hierarchy.user, created.id, MissionUpdate(xpReward=200)
    )
    await service.delete_mission(hierarchy.user, created.id)

    assert listed.total_items == 1
    assert listed.data[0].title == "Complete lessons"
    assert updated.xp_reward == 200
    stored = await db_session.get(Mission, created.id)
    assert stored.msn_is_deleted is True
