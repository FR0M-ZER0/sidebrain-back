from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.enums.badge_criteria_enum import BadgeCriteriaEnum
from sidebrain_back.enums.badge_progress_status_enum import (
    BadgeProgressStatusEnum,
)
from sidebrain_back.models.badge_progress_model import BadgeProgress
from sidebrain_back.repositories.badge_progress_repository import (
    BadgeProgressRepository,
)
from sidebrain_back.repositories.badge_repository import BadgeRepository
from sidebrain_back.repositories.generation_repository import (
    GenerationRepository,
)
from sidebrain_back.repositories.mission_progress_repository import (
    MissionProgressRepository,
)
from sidebrain_back.repositories.quiz_repository import QuizRepository
from sidebrain_back.repositories.track_repository import TrackRepository
from sidebrain_back.schemas.generation_schema import (
    GeneratedTrack,
    GenerationInput,
)
from sidebrain_back.schemas.quiz_schema import (
    QuizAnswerCreateRequest,
    QuizEvaluationResult,
)
from sidebrain_back.schemas.track_schema import TrackCreate
from sidebrain_back.services.badge_progress_service import BadgeProgressService
from sidebrain_back.services.generation_service import GenerationService
from sidebrain_back.services.mission_progress_service import (
    MissionProgressService,
)
from sidebrain_back.services.quiz_service import QuizService
from sidebrain_back.services.track_service import TrackService


def _quiz_service(db):
    return QuizService(
        QuizRepository(db),
        db,
        evaluator=SimpleNamespace(
            evaluate=lambda _question, answer: QuizEvaluationResult(
                rate=AnswerRateEnum(answer),
                reason="A resposta recebeu a classificação esperada.",
            )
        ),
        mission_progress_service=MissionProgressService(
            MissionProgressRepository(db), db
        ),
        badge_progress_service=BadgeProgressService(
            BadgeProgressRepository(db), db
        ),
    )


async def _badge_statuses(db, user_id):
    badges, _ = await BadgeRepository(db).list(user_id, 0, 100)
    return {
        badge.bdg_criteria: badge.badge_progresses[0].bpg_status
        for badge in badges
    }


@pytest.mark.anyio
async def test_answer_completes_global_badges_from_user_activity(
    db_session,
    learning_hierarchy_factory,
    quiz_factory,
    mission_factory,
    mission_progress_factory,
    badge_factory,
):
    hierarchy = await learning_hierarchy_factory()
    quiz = await quiz_factory(hierarchy.lesson)
    mission = await mission_factory(hierarchy.step, xp_reward=40)
    await mission_progress_factory(
        hierarchy.user,
        mission,
        status=BadgeProgressStatusEnum.DONE,
        score=100,
    )
    criteria = [
        (BadgeCriteriaEnum.XP_GAINED, 40),
        (BadgeCriteriaEnum.TRACKS_COMPLETED, 1),
        (BadgeCriteriaEnum.LESSONS_COMPLETED, 1),
        (BadgeCriteriaEnum.RIGHT_ANSWERS, 1),
        (BadgeCriteriaEnum.DAY_STREAK, 1),
        (BadgeCriteriaEnum.TRACKS_CREATED, 1),
        (BadgeCriteriaEnum.MISSIONS_COMPLETED, 1),
    ]
    for badge_criteria, target in criteria:
        await badge_factory(
            name=f"Badge {badge_criteria.value}",
            criteria=badge_criteria,
            criteria_value=target,
        )
    user_id = hierarchy.user.usr_id
    await db_session.commit()

    result = await _quiz_service(db_session).submit_quiz_answer(
        hierarchy.user,
        quiz.qui_id,
        QuizAnswerCreateRequest(text="good"),
    )
    await db_session.commit()

    assert result.rate is AnswerRateEnum.GOOD
    assert await _badge_statuses(db_session, user_id) == {
        badge_criteria: BadgeProgressStatusEnum.DONE
        for badge_criteria, _target in criteria
    }
    streak = await BadgeProgressRepository(db_session).get_day_streak(user_id)
    assert streak.dst_value == 1
    persisted = list(
        (
            await db_session.scalars(
                select(BadgeProgress).where(
                    BadgeProgress.bpg_user_id == user_id
                )
            )
        ).all()
    )
    assert len(persisted) == len(criteria)


@pytest.mark.anyio
async def test_streak_badge_advances_once_per_day_and_resets_after_gap(
    db_session, user_factory, badge_factory
):
    user = await user_factory()
    await badge_factory(
        name="Streak de 3 dias",
        criteria=BadgeCriteriaEnum.DAY_STREAK,
        criteria_value=3,
    )
    service = BadgeProgressService(
        BadgeProgressRepository(db_session), db_session
    )
    await service.register_activity_and_update_badges(user.usr_id)
    await service.register_activity_and_update_badges(user.usr_id)
    same_day = await BadgeProgressRepository(db_session).get_day_streak(
        user.usr_id
    )
    assert same_day.dst_value == 1

    same_day.dst_updated_at -= timedelta(days=1)
    await db_session.flush()
    await service.register_activity_and_update_badges(user.usr_id)
    advanced = await BadgeProgressRepository(db_session).get_day_streak(
        user.usr_id
    )
    assert advanced.dst_value == 2
    row = (
        await db_session.scalars(
            select(BadgeProgress).where(
                BadgeProgress.bpg_user_id == user.usr_id
            )
        )
    ).one()
    assert row.bpg_status is BadgeProgressStatusEnum.IN_PROGRESS

    advanced.dst_updated_at -= timedelta(days=3)
    await db_session.flush()
    await service.register_activity_and_update_badges(user.usr_id)
    reset = await BadgeProgressRepository(db_session).get_day_streak(
        user.usr_id
    )
    assert reset.dst_value == 1


@pytest.mark.anyio
async def test_legacy_track_creation_updates_tracks_created_badges(
    db_session, user_factory, badge_factory
):
    user = await user_factory()
    user_id = user.usr_id
    await badge_factory(
        name="Duas trilhas",
        criteria=BadgeCriteriaEnum.TRACKS_CREATED,
        criteria_value=2,
    )
    badge_progress = BadgeProgressService(
        BadgeProgressRepository(db_session), db_session
    )
    service = TrackService(
        TrackRepository(db_session),
        db_session,
        badge_progress_service=badge_progress,
    )
    await service.create_track(
        SimpleNamespace(usr_id=user_id), TrackCreate(title="Primeira")
    )
    assert (await _badge_statuses(db_session, user_id))[
        BadgeCriteriaEnum.TRACKS_CREATED
    ] is BadgeProgressStatusEnum.IN_PROGRESS
    await service.create_track(
        SimpleNamespace(usr_id=user_id), TrackCreate(title="Segunda")
    )
    assert (await _badge_statuses(db_session, user_id))[
        BadgeCriteriaEnum.TRACKS_CREATED
    ] is BadgeProgressStatusEnum.DONE


@pytest.mark.anyio
async def test_ai_track_persistence_updates_track_creation_badges(
    db_session, user_factory, badge_factory, monkeypatch
):
    user = await user_factory()
    user_id = user.usr_id
    await badge_factory(
        name="Trilha criada",
        criteria=BadgeCriteriaEnum.TRACKS_CREATED,
        criteria_value=1,
    )
    await db_session.commit()
    mission_progress = BadgeProgressService(
        BadgeProgressRepository(db_session), db_session
    )
    generated = {
        "icon": "📘",
        "title": "Python",
        "description": "Introdução",
        "steps": [
            {
                "position": 1,
                "level": "beginner",
                "title": "Base",
                "lessons": [
                    {
                        "position": position,
                        "title": f"Lição {position}",
                        "text": "Conteúdo",
                        "quiz": {"question": f"Pergunta {position}"},
                    }
                    for position in range(1, 4)
                ],
                "mission": {
                    "title": "Conclua as lições",
                    "difficulty": "easy",
                    "xp_reward": 10,
                    "criteria": "number_of_lessons_completed",
                    "criteria_value": 3,
                },
            }
        ],
    }
    service = GenerationService(
        GenerationRepository(db_session),
        db_session,
        badge_progress_service=mission_progress,
    )
    monkeypatch.setattr(
        service,
        "generate_with_ai",
        lambda _payload, _context=None: GeneratedTrack.model_validate(
            generated
        ),
    )
    payload = GenerationInput(
        request_id=uuid4(), user_id=user_id, goal="Python", topic="Python"
    )
    await service.generate(payload)

    assert (await _badge_statuses(db_session, user_id))[
        BadgeCriteriaEnum.TRACKS_CREATED
    ] is BadgeProgressStatusEnum.DONE
