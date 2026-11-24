from datetime import UTC, datetime, timedelta

import pytest

from sidebrain_back.repositories.job_update_repository import (
    JobUpdateRepository,
)
from sidebrain_back.repositories.step_preparation_repository import (
    StepPreparationRepository,
)
from sidebrain_back.repositories.step_summary_generation_repository import (
    StepSummaryGenerationRepository,
)


@pytest.mark.anyio
async def test_deleted_preparation_source_is_unavailable(
    db_session, learning_hierarchy_factory
):
    from uuid import uuid4

    from sidebrain_back.enums.step_level_enum import StepLevelEnum
    from sidebrain_back.models.step_model import Step

    hierarchy = await learning_hierarchy_factory()
    target = Step(
        stp_id=uuid4(),
        stp_track_id=hierarchy.track.trk_id,
        stp_level=StepLevelEnum.INTERMEDIATE,
        stp_title="Target",
    )
    db_session.add(target)
    await db_session.flush()
    repository = StepPreparationRepository(db_session)
    await repository.create(
        task_id="deleted-source",
        user_id=hierarchy.user.usr_id,
        track_id=hierarchy.track.trk_id,
        source_step_id=hierarchy.step.stp_id,
        target_step_id=target.stp_id,
    )
    assert (
        await repository.get_accessible(
            "deleted-source", hierarchy.user.usr_id
        )
        is not None
    )
    hierarchy.step.stp_is_deleted = True
    await db_session.flush()
    assert (
        await repository.get_accessible(
            "deleted-source", hierarchy.user.usr_id
        )
        is None
    )
    assert (
        await JobUpdateRepository(db_session).step_preparation(
            "deleted-source", hierarchy.user.usr_id
        )
        is None
    )


@pytest.mark.anyio
async def test_latest_summary_generation_wins(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    repository = StepSummaryGenerationRepository(db_session)

    first = await repository.reserve(hierarchy.step.stp_id)
    second = await repository.reserve(hierarchy.step.stp_id)

    assert second == first + 1
    assert (
        await repository.finish(hierarchy.step.stp_id, first, "completed")
        is False
    )
    assert (
        await repository.finish(hierarchy.step.stp_id, second, "completed")
        is True
    )


@pytest.mark.anyio
async def test_preparation_expires_twenty_four_hours_after_first_terminal(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    preparations = StepPreparationRepository(db_session)
    preparation = await preparations.create(
        task_id="expiration-task",
        user_id=hierarchy.user.usr_id,
        track_id=hierarchy.track.trk_id,
        source_step_id=hierarchy.step.stp_id,
        target_step_id=hierarchy.step.stp_id,
    )
    assert await preparations.finish("expiration-task", "completed")
    first_terminal = preparation.finished_at
    assert first_terminal is not None
    assert not await preparations.finish("expiration-task", "failed")
    assert preparation.finished_at == first_terminal

    preparation.finished_at = datetime.now(UTC) - timedelta(hours=24)
    await db_session.flush()
    assert (
        await JobUpdateRepository(db_session).step_preparation(
            preparation.task_id, hierarchy.user.usr_id
        )
        is None
    )
