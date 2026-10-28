from uuid import uuid4

import pytest

from sidebrain_back.models.mission_model import Mission
from sidebrain_back.repositories.mission_progress_repository import (
    LessonProgressFacts,
)
from sidebrain_back.services.mission_progress_service import (
    MissionProgressService,
)


@pytest.mark.parametrize(
    "criteria",
    [
        "complete_a_step",
        "complete_a_track",
        "number_of_steps_completed",
        "number_of_lessons_completed",
        "get_all_answer_right_in_a_lesson",
        "get_all_answers_right",
    ],
)
@pytest.mark.parametrize("empty_lesson", [True, False])
def test_empty_content_never_completes_a_mission(criteria, empty_lesson):
    step_id = uuid4()
    lessons = (
        [LessonProgressFacts(step_id, uuid4(), 0, 0, 0)]
        if empty_lesson
        else []
    )
    mission = Mission(
        msn_step_id=step_id, msn_criteria=criteria, msn_criteria_value=1
    )
    assert MissionProgressService.evaluate_mission(
        mission, {step_id: lessons}
    ) == ("idle", 0)


@pytest.mark.parametrize(
    "criterion,target,expected",
    [
        ("number_of_lessons_completed", 3, ("in_progress", 33)),
        ("number_of_lessons_completed", 1, ("done", 100)),
        ("complete_a_step", 1, ("in_progress", 50)),
        ("get_all_answer_right_in_a_lesson", 1, ("in_progress", 50)),
        ("get_all_answers_right", 1, ("in_progress", 25)),
    ],
)
def test_partial_progress_uses_distinct_quizzes_in_the_mission_step(
    criterion, target, expected
):
    step_id, other_id = uuid4(), uuid4()
    steps = {
        step_id: [
            LessonProgressFacts(step_id, uuid4(), 2, 2, 1),
            LessonProgressFacts(step_id, uuid4(), 2, 0, 0),
        ],
        other_id: [LessonProgressFacts(other_id, uuid4(), 3, 3, 3)],
    }
    mission = Mission(
        msn_step_id=step_id, msn_criteria=criterion, msn_criteria_value=target
    )
    assert MissionProgressService.evaluate_mission(mission, steps) == expected


def test_eighty_percent_preparation_threshold_does_not_complete_step():
    step_id = uuid4()
    lessons = [
        LessonProgressFacts(step_id, uuid4(), 1, 1, 1) for _ in range(4)
    ]
    lessons.append(LessonProgressFacts(step_id, uuid4(), 1, 0, 0))
    mission = Mission(
        msn_step_id=step_id,
        msn_criteria="complete_a_step",
        msn_criteria_value=1,
    )
    assert MissionProgressService.evaluate_mission(
        mission, {step_id: lessons}
    ) == ("in_progress", 80)
