import asyncio
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, func, select

from sidebrain_back.core.database import async_session, engine, get_db
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.enums.mission_criteria_enum import MissionCriteriaEnum
from sidebrain_back.models import (
    Answer,
    Lesson,
    Mission,
    MissionProgress,
    Quiz,
    Step,
    Track,
    User,
)
from sidebrain_back.repositories.mission_progress_repository import (
    MissionProgressRepository,
)
from sidebrain_back.repositories.mission_repository import MissionRepository
from sidebrain_back.repositories.quiz_repository import QuizRepository
from sidebrain_back.repositories.ranking_repository import RankingRepository
from sidebrain_back.repositories.track_repository import TrackRepository
from sidebrain_back.routers.v1.auth_router import get_current_user
from sidebrain_back.schemas.quiz_schema import (
    QuizAnswerCreateRequest,
    QuizEvaluationResult,
)
from sidebrain_back.schemas.track_schema import TrackResponse
from sidebrain_back.services.mission_progress_service import (
    MissionProgressService,
)
from sidebrain_back.services.quiz_evaluation_service import (
    QuizEvaluationService,
)
from sidebrain_back.services.quiz_service import QuizService
from sidebrain_back.services.track_service import TrackService


def progress_service(db):
    return MissionProgressService(MissionProgressRepository(db), db)


def quiz_service(db):
    return QuizService(
        QuizRepository(db),
        db,
        evaluator=SimpleNamespace(
            evaluate=lambda _q, answer: QuizEvaluationResult(
                rate=AnswerRateEnum(answer),
                reason="A resposta recebeu a classificação esperada.",
            )
        ),
        mission_progress_service=progress_service(db),
    )


async def submit(db, user_id, quiz_id, rate="good"):
    return await quiz_service(db).submit_quiz_answer(
        SimpleNamespace(usr_id=user_id),
        quiz_id,
        QuizAnswerCreateRequest(text=rate),
    )


async def stored_progress(db, user_id, mission_id):
    return await db.scalar(
        select(MissionProgress)
        .where(
            MissionProgress.mpg_user_id == user_id,
            MissionProgress.mpg_mission_id == mission_id,
        )
        .execution_options(populate_existing=True)
    )


@pytest.mark.anyio
async def test_http_answer_updates_progress_and_recalculation_is_idempotent(
    db_session,
    learning_hierarchy_factory,
    quiz_factory,
    mission_factory,
    test_app,
    monkeypatch,
):
    h = await learning_hierarchy_factory()
    quiz = await quiz_factory(h.lesson)
    mission = await mission_factory(h.step, criteria_value=1)
    user_id, quiz_id = h.user.usr_id, quiz.qui_id
    step_id, mission_id, track_id = (
        h.step.stp_id,
        mission.msn_id,
        h.track.trk_id,
    )
    await db_session.commit()

    async def override_db():
        yield db_session

    async def no_enqueue(_service, _step_id):
        return None

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        usr_id=user_id
    )
    monkeypatch.setattr(
        QuizEvaluationService,
        "evaluate",
        lambda *_args: QuizEvaluationResult(
            rate=AnswerRateEnum.GOOD,
            reason="A resposta está correta.",
        ),
    )
    monkeypatch.setattr(
        TrackService, "enqueue_next_step_preparation", no_enqueue
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        recalculation_url = (
            f"/api/v1/steps/{step_id}/missions/recalculate-progress"
        )
        assert (await client.post(recalculation_url)).status_code == 204
        before = (await client.get(f"/api/v1/missions/{mission_id}")).json()
        assert before["missionProgresses"][0]["status"] == "idle"
        result = await client.post(
            f"/api/v1/quizzes/{quiz_id}/answers", json={"text": "Resposta"}
        )
        assert result.status_code == 201
        # Outra requisição usa uma sessão limpa, como na API em produção.
        db_session.expire_all()
        completed = (await client.get(f"/api/v1/missions/{mission_id}")).json()
        progress = completed["missionProgresses"][0]
        assert (progress["status"], progress["score"]) == ("done", 100)
        assert progress["finished_in"] is not None
        assert (await client.post(recalculation_url)).status_code == 204
        after = (await client.get(f"/api/v1/missions/{mission_id}")).json()
        assert after["missionProgresses"] == completed["missionProgresses"]
        track = (await client.get(f"/api/v1/tracks/{track_id}")).json()
        assert (
            track["steps"][0]["missions"][0]["mission_progresses"][0]["score"]
            == 100
        )
        missing = await client.post(
            f"/api/v1/steps/{uuid4()}/missions/recalculate-progress"
        )
        assert missing.status_code == 404


@pytest.mark.anyio
async def test_all_criteria_follow_answers_and_preserve_completed_progress(
    db_session,
    learning_hierarchy_factory,
    lesson_factory,
    step_factory,
    quiz_factory,
    mission_factory,
):
    h = await learning_hierarchy_factory()
    lessons = [h.lesson]
    for position in (2, 3):
        lessons.append(await lesson_factory(h.step, position=position))
    quizzes = [await quiz_factory(lesson) for lesson in lessons]
    future_step = await step_factory(h.track)
    targets = {
        "number_of_lessons_completed": 3,
        "number_of_steps_completed": 2,
    }
    missions = {
        criterion.value: await mission_factory(
            h.step,
            criteria=criterion.value,
            criteria_value=targets.get(criterion.value, 1),
        )
        for criterion in MissionCriteriaEnum
    }
    other_mission = await mission_factory(
        future_step, criteria="get_all_answers_right", criteria_value=1
    )
    user_id, track_id, step_id = h.user.usr_id, h.track.trk_id, h.step.stp_id
    quiz_ids = [quiz.qui_id for quiz in quizzes]
    ids = {key: item.msn_id for key, item in missions.items()}
    other_id, future_id = other_mission.msn_id, future_step.stp_id
    await db_session.commit()

    service = progress_service(db_session)
    await service.recalculate_missions_by_step_id(user_id, step_id)
    assert (
        await stored_progress(db_session, user_id, ids["complete_a_step"])
    ).mpg_status == "idle"
    await submit(db_session, user_id, quiz_ids[0], "wrong")
    await submit(db_session, user_id, quiz_ids[0], "wrong")
    count = await stored_progress(
        db_session, user_id, ids["number_of_lessons_completed"]
    )
    assert (count.mpg_status, count.mpg_score) == ("in_progress", 33)
    all_correct = await stored_progress(
        db_session, user_id, ids["get_all_answers_right"]
    )
    assert (all_correct.mpg_status, all_correct.mpg_score) == (
        "in_progress",
        0,
    )

    await submit(db_session, user_id, quiz_ids[0])
    perfect = await stored_progress(
        db_session, user_id, ids["get_all_answer_right_in_a_lesson"]
    )
    assert perfect.mpg_status == "done"
    finished_at = perfect.mpg_finished_in
    assert finished_at is not None
    for quiz_id in quiz_ids[1:]:
        await submit(db_session, user_id, quiz_id, "perfect")
    for criterion in (
        "number_of_lessons_completed",
        "complete_a_step",
        "get_all_answers_right",
    ):
        row = await stored_progress(db_session, user_id, ids[criterion])
        assert (row.mpg_status, row.mpg_score) == ("done", 100)
    for criterion in ("complete_a_track", "number_of_steps_completed"):
        row = await stored_progress(db_session, user_id, ids[criterion])
        assert (row.mpg_status, row.mpg_score) == ("in_progress", 50)
    # Etapas futuras vazias impedem a conclusão e não recebem acertos alheios.
    assert (
        await stored_progress(db_session, user_id, other_id)
    ).mpg_status == "idle"

    future_step = await db_session.get(Step, future_id)
    future_lesson = await lesson_factory(future_step)
    future_quiz = await quiz_factory(future_lesson)
    future_quiz_id = future_quiz.qui_id
    await db_session.commit()
    await submit(db_session, user_id, future_quiz_id)
    await submit(db_session, user_id, quiz_ids[0], "wrong")
    await service.recalculate_missions_by_step_id(user_id, step_id)
    perfect = await stored_progress(
        db_session, user_id, ids["get_all_answer_right_in_a_lesson"]
    )
    assert perfect.mpg_finished_in == finished_at
    for mission_id in ids.values():
        assert (
            await stored_progress(db_session, user_id, mission_id)
        ).mpg_status == "done"
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(MissionProgress)
            .where(MissionProgress.mpg_user_id == user_id)
        )
        == 7
    )

    # O GET de missão e a hierarquia da trilha expõem o progresso persistido.
    mission = await MissionRepository(db_session).get(
        user_id, ids["complete_a_step"]
    )
    assert mission.mission_progresses[0].mpg_score == 100
    track = await TrackRepository(db_session).get(user_id, track_id)
    response = TrackResponse.model_validate(track)
    assert all(
        m.mission_progresses[0].status == "done"
        for s in response.steps
        for m in s.missions
    )
    ranking = await RankingRepository(db_session).get_user_ranking(user_id)
    assert ranking.xp == 700
    assert ranking.missions_completed == 7


@pytest.mark.anyio
async def test_counts_ignore_manual_status_and_foreign_answers(
    db_session,
    learning_hierarchy_factory,
    quiz_factory,
    answer_factory,
    mission_factory,
    user_factory,
    lesson_factory,
):
    h = await learning_hierarchy_factory(lesson_status="done")
    first = await quiz_factory(h.lesson)
    second = await quiz_factory(h.lesson)
    deleted = await quiz_factory(h.lesson, deleted=True)
    extra_lesson = await lesson_factory(h.step, position=2, deleted=True)
    await quiz_factory(extra_lesson)
    foreign = await user_factory()
    await answer_factory(first, foreign)
    await answer_factory(second, foreign)
    await answer_factory(deleted, h.user)
    mission = await mission_factory(h.step, criteria_value=1)
    deleted_mission = await mission_factory(h.step, deleted=True)
    user_id, step_id, mission_id = h.user.usr_id, h.step.stp_id, mission.msn_id
    first_id, second_id, deleted_id = (
        first.qui_id,
        second.qui_id,
        deleted_mission.msn_id,
    )
    await db_session.commit()
    service = progress_service(db_session)
    await service.recalculate_missions_by_step_id(user_id, step_id)
    row = await stored_progress(db_session, user_id, mission_id)
    assert (row.mpg_status, row.mpg_score) == ("idle", 0)
    assert await stored_progress(db_session, user_id, deleted_id) is None
    await submit(db_session, user_id, first_id, "almost_got_it")
    assert (
        await stored_progress(db_session, user_id, mission_id)
    ).mpg_status == "in_progress"
    assert (
        await stored_progress(db_session, user_id, mission_id)
    ).mpg_score == 0
    await submit(db_session, user_id, second_id, "wrong")
    assert (
        await stored_progress(db_session, user_id, mission_id)
    ).mpg_status == "done"


@pytest.mark.anyio
@pytest.mark.parametrize("unavailable", ["owner", "step", "track", "missing"])
async def test_recalculation_conceals_unavailable_steps(
    db_session,
    learning_hierarchy_factory,
    unavailable,
):
    h = await learning_hierarchy_factory(
        step_deleted=unavailable == "step",
        track_deleted=unavailable == "track",
    )
    user_id = uuid4() if unavailable == "owner" else h.user.usr_id
    step_id = uuid4() if unavailable == "missing" else h.step.stp_id
    await db_session.commit()
    with pytest.raises(ProblemDetailError) as error:
        await progress_service(db_session).recalculate_missions_by_step_id(
            user_id, step_id
        )
    assert error.value.status_code == 404


@pytest.mark.anyio
async def test_progress_failure_rolls_back_answer_and_lesson(
    db_session,
    learning_hierarchy_factory,
    quiz_factory,
    mission_factory,
    monkeypatch,
):
    h = await learning_hierarchy_factory()
    quiz = await quiz_factory(h.lesson)
    await mission_factory(h.step, criteria_value=1)
    user_id, quiz_id, lesson_id = h.user.usr_id, quiz.qui_id, h.lesson.lsn_id
    await db_session.commit()

    async def fail_flush(_repository):
        raise RuntimeError("simulated persistence failure")

    monkeypatch.setattr(MissionProgressRepository, "flush", fail_flush)
    with pytest.raises(ProblemDetailError):
        await submit(db_session, user_id, quiz_id)
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(Answer)
            .where(Answer.ans_question_id == quiz_id)
        )
        == 0
    )
    assert (await db_session.get(Lesson, lesson_id)).lsn_status == "idle"
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(MissionProgress)
            .where(MissionProgress.mpg_user_id == user_id)
        )
        == 0
    )


@pytest.mark.anyio
async def test_concurrent_answers_complete_one_progress_without_double_xp(
    database_schema,
):
    user_id, track_id, step_id, lesson_id, mission_id = [
        uuid4() for _ in range(5)
    ]
    quiz_ids = [uuid4(), uuid4()]
    try:
        async with async_session() as db:
            db.add(
                User(
                    usr_id=user_id,
                    usr_name="Concurrent",
                    usr_email=f"{user_id}@test.com",
                    usr_password_hash="test",
                )
            )
            await db.flush()
            db.add(
                Track(trk_id=track_id, trk_user_id=user_id, trk_title="Python")
            )
            await db.flush()
            db.add(
                Step(
                    stp_id=step_id,
                    stp_track_id=track_id,
                    stp_level="beginner",
                    stp_title="Base",
                )
            )
            await db.flush()
            db.add(
                Lesson(
                    lsn_id=lesson_id,
                    lsn_step_id=step_id,
                    lsn_title="Base",
                    lsn_text="Texto",
                    lsn_position=1,
                )
            )
            db.add(
                Mission(
                    msn_id=mission_id,
                    msn_step_id=step_id,
                    msn_title="Conclua a etapa",
                    msn_difficulty="easy",
                    msn_xp_reward=50,
                    msn_criteria="complete_a_step",
                    msn_criteria_value=1,
                )
            )
            await db.flush()
            db.add_all(
                [
                    Quiz(
                        qui_id=q,
                        qui_lesson_id=lesson_id,
                        qui_question="Pergunta",
                    )
                    for q in quiz_ids
                ]
            )
            await db.commit()

        async def respond(quiz_id):
            async with async_session() as db:
                await submit(db, user_id, quiz_id)

        await asyncio.wait_for(
            asyncio.gather(*(respond(q) for q in quiz_ids)), timeout=10
        )
        async with async_session() as db:
            row = await stored_progress(db, user_id, mission_id)
            assert (row.mpg_status, row.mpg_score) == ("done", 100)
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(MissionProgress)
                    .where(MissionProgress.mpg_user_id == user_id)
                )
                == 1
            )
            assert (
                await RankingRepository(db).get_user_ranking(user_id)
            ).xp == 50
    finally:
        async with async_session() as db:
            await db.execute(delete(User).where(User.usr_id == user_id))
            await db.commit()
        await engine.dispose()
