from types import SimpleNamespace
from uuid import UUID

from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.enums.step_status_enum import StepStatusEnum
from sidebrain_back.tasks.prepare_next_step_content_task import _build_context


def _step(step_id: int, level: StepLevelEnum):
    return SimpleNamespace(
        stp_id=UUID(int=step_id),
        stp_level=level,
        stp_title=level.value.title(),
        stp_status=StepStatusEnum.IDLE,
        stp_is_deleted=False,
        lessons=[],
    )


def test_incremental_generation_context_includes_only_lower_levels_in_order():
    track = SimpleNamespace(
        trk_id=UUID(int=100),
        trk_title="Trilha",
        trk_description="Descrição",
    )
    pro = _step(1, StepLevelEnum.PRO)
    intermediate = _step(2, StepLevelEnum.INTERMEDIATE)
    advanced = _step(3, StepLevelEnum.ADVANCED)
    beginner = _step(4, StepLevelEnum.BEGINNER)
    steps = [pro, intermediate, advanced, beginner]
    for step in steps:
        step.track = track
    track.steps = steps

    context = _build_context(intermediate)

    previous_titles = [step["title"] for step in context["previous_steps"]]
    assert previous_titles == ["Beginner"]
