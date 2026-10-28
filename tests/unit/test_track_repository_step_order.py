from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.repositories.track_repository import TrackRepository


class FakeScalars:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, current_step, steps):
        self.current_step = current_step
        self.steps = steps

    async def scalar(self, _statement):
        return self.current_step

    async def scalars(self, _statement):
        return FakeScalars(self.steps)


def _step(track_id, step_id, level, *, lessons=None):
    return SimpleNamespace(
        stp_id=UUID(int=step_id),
        stp_track_id=track_id,
        stp_level=level,
        stp_updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        lessons=lessons or [],
        missions=[],
    )


@pytest.mark.anyio
async def test_next_eligible_step_uses_level_order_not_uuid_order():
    track_id = uuid4()
    beginner = _step(track_id, 4, StepLevelEnum.BEGINNER, lessons=[object()])
    intermediate = _step(track_id, 3, StepLevelEnum.INTERMEDIATE)
    advanced = _step(track_id, 2, StepLevelEnum.ADVANCED)
    pro = _step(track_id, 1, StepLevelEnum.PRO)
    repository = TrackRepository(
        FakeSession(beginner, [pro, advanced, intermediate, beginner])
    )

    next_step = await repository.get_next_eligible_step(beginner.stp_id)
    assert next_step is intermediate

    intermediate.lessons.append(object())
    assert await repository.get_next_eligible_step(beginner.stp_id) is advanced
