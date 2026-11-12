from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest

from sidebrain_back.core.database import get_db
from sidebrain_back.core.security import create_access_token
from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.enums.mission_progress_status_enum import (
    MissionProgressStatusEnum,
)
from sidebrain_back.models.user_model import User
from sidebrain_back.routers.v1.auth_router import get_current_user
from sidebrain_back.schemas.quiz_schema import QuizEvaluationResult
from sidebrain_back.services.mission_progress_service import (
    MissionProgressService,
)
from sidebrain_back.services.quiz_evaluation_service import (
    QuizEvaluationService,
)
from sidebrain_back.services.track_service import TrackService


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.usr_id, user.usr_token_version)
    return {"Authorization": f"Bearer {token}"}


@asynccontextmanager
async def _authenticated_http_client(
    db_session,
    test_app,
    monkeypatch,
    *,
    rate: AnswerRateEnum = AnswerRateEnum.GOOD,
):
    """Configura AsyncClient HTTP real com JWT e avaliação determinística."""

    async def override_db():
        yield db_session

    async def no_enqueue(_service, _step_id):
        return None

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides.pop(get_current_user, None)
    monkeypatch.setattr(
        QuizEvaluationService,
        "evaluate",
        lambda *_args: QuizEvaluationResult(
            rate=rate,
            reason="Resposta avaliada para validação de consistência.",
        ),
    )
    monkeypatch.setattr(
        TrackService,
        "enqueue_next_step_preparation",
        no_enqueue,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        yield client


async def _assert_xp_consistency(
    client: httpx.AsyncClient,
    db_session,
    user_id: UUID,
    headers: dict[str, str],
    *,
    expected_xp: int,
    expected_missions: int,
    expected_position: int | None = None,
) -> int:
    """Valida igualdade entre /users/me, /rankings/me e /rankings."""
    db_session.expire_all()

    profile_resp = await client.get("/api/v1/users/me", headers=headers)
    assert profile_resp.status_code == 200
    profile = profile_resp.json()
    assert profile["xp"] == expected_xp
    assert profile["missionsCompleted"] == expected_missions

    my_rank_resp = await client.get("/api/v1/rankings/me", headers=headers)
    assert my_rank_resp.status_code == 200
    my_rank = my_rank_resp.json()
    assert my_rank["userId"] == str(user_id)
    assert my_rank["xp"] == expected_xp
    assert my_rank["missionsCompleted"] == expected_missions

    list_resp = await client.get(
        "/api/v1/rankings?page=1&page_size=100",
        headers=headers,
    )
    assert list_resp.status_code == 200
    entries = list_resp.json()["data"]
    matching = [item for item in entries if item["userId"] == str(user_id)]
    assert len(matching) == 1
    assert matching[0] == my_rank

    if expected_position is not None:
        assert my_rank["position"] == expected_position

    return my_rank["position"]


@pytest.mark.anyio
async def test_quiz_completion_updates_profile_and_ranking_immediately(
    db_session,
    learning_hierarchy_factory,
    quiz_factory,
    mission_factory,
    mission_progress_factory,
    test_app,
    monkeypatch,
):
    """Conclusão via quiz reflete no perfil e ranking sem fila."""
    hierarchy = await learning_hierarchy_factory()
    user_a = hierarchy.user
    quiz = await quiz_factory(hierarchy.lesson)
    await mission_factory(
        hierarchy.step,
        title="Primeira Missão",
        xp_reward=150,
        criteria="number_of_lessons_completed",
        criteria_value=1,
    )

    now = datetime.now(UTC).replace(tzinfo=None)
    user_a.usr_created_at = now
    other_hierarchy = await learning_hierarchy_factory()
    user_b = other_hierarchy.user
    user_b.usr_name = "Competidor B"
    user_b.usr_created_at = now - timedelta(minutes=5)
    other_mission = await mission_factory(
        other_hierarchy.step,
        title="Missão B",
        xp_reward=100,
    )
    await mission_progress_factory(
        user_b,
        other_mission,
        status=MissionProgressStatusEnum.DONE,
    )
    user_a_id, headers_a = user_a.usr_id, _auth_headers(user_a)
    user_b_id, headers_b = user_b.usr_id, _auth_headers(user_b)
    quiz_id = quiz.qui_id
    await db_session.commit()

    async with _authenticated_http_client(
        db_session, test_app, monkeypatch
    ) as client:
        # Antes da conclusão: user_a (0 XP) atrás de user_b (100 XP).
        await _assert_xp_consistency(
            client,
            db_session,
            user_b_id,
            headers_b,
            expected_xp=100,
            expected_missions=1,
            expected_position=1,
        )
        await _assert_xp_consistency(
            client,
            db_session,
            user_a_id,
            headers_a,
            expected_xp=0,
            expected_missions=0,
            expected_position=2,
        )

        submit_resp = await client.post(
            f"/api/v1/quizzes/{quiz_id}/answers",
            json={"text": "Resposta correta"},
            headers=headers_a,
        )
        assert submit_resp.status_code == 201

        # Imediatamente após o commit, sem worker nem fila:
        await _assert_xp_consistency(
            client,
            db_session,
            user_a_id,
            headers_a,
            expected_xp=150,
            expected_missions=1,
            expected_position=1,
        )
        await _assert_xp_consistency(
            client,
            db_session,
            user_b_id,
            headers_b,
            expected_xp=100,
            expected_missions=1,
            expected_position=2,
        )


@pytest.mark.anyio
async def test_partial_submission_and_precommit_failure_preserve_xp(
    db_session,
    learning_hierarchy_factory,
    lesson_factory,
    quiz_factory,
    mission_factory,
    test_app,
    monkeypatch,
):
    """Progresso parcial e rollback em falha não alteram XP nem ranking."""
    hierarchy = await learning_hierarchy_factory()
    user = hierarchy.user
    lesson_2 = await lesson_factory(hierarchy.step, position=2)
    quiz_1 = await quiz_factory(hierarchy.lesson)
    quiz_2 = await quiz_factory(lesson_2)
    await mission_factory(
        hierarchy.step,
        title="Duas aulas",
        xp_reward=200,
        criteria="number_of_lessons_completed",
        criteria_value=2,
    )
    user_id, headers = user.usr_id, _auth_headers(user)
    quiz_1_id, quiz_2_id = quiz_1.qui_id, quiz_2.qui_id
    await db_session.commit()

    async with _authenticated_http_client(
        db_session, test_app, monkeypatch
    ) as client:
        partial_resp = await client.post(
            f"/api/v1/quizzes/{quiz_1_id}/answers",
            json={"text": "Parcial"},
            headers=headers,
        )
        assert partial_resp.status_code == 201

        initial_pos = await _assert_xp_consistency(
            client,
            db_session,
            user_id,
            headers,
            expected_xp=0,
            expected_missions=0,
        )

        async def fail_recalculation(*_args, **_kwargs):
            raise RuntimeError("Falha simulada antes do commit")

        monkeypatch.setattr(
            MissionProgressService,
            "update_missions_by_track_id",
            fail_recalculation,
        )
        failed_resp = await client.post(
            f"/api/v1/quizzes/{quiz_2_id}/answers",
            json={"text": "Falha"},
            headers=headers,
        )
        assert failed_resp.status_code == 500

        await _assert_xp_consistency(
            client,
            db_session,
            user_id,
            headers,
            expected_xp=0,
            expected_missions=0,
            expected_position=initial_pos,
        )


@pytest.mark.anyio
async def test_profile_and_ranking_share_identical_xp_and_completed_count(
    db_session,
    learning_hierarchy_factory,
    mission_factory,
    mission_progress_factory,
    user_factory,
    test_app,
    monkeypatch,
):
    """GET/PUT /users/me, /rankings/me e /rankings usam a mesma regra."""
    hierarchy = await learning_hierarchy_factory()
    user_multi = hierarchy.user
    user_zero = await user_factory(name="Zero XP User")

    m_done_1 = await mission_factory(hierarchy.step, xp_reward=80)
    m_done_2 = await mission_factory(hierarchy.step, xp_reward=120)
    m_in_progress = await mission_factory(hierarchy.step, xp_reward=500)
    m_idle = await mission_factory(hierarchy.step, xp_reward=300)

    await mission_progress_factory(
        user_multi, m_done_1, status=MissionProgressStatusEnum.DONE
    )
    await mission_progress_factory(
        user_multi, m_done_2, status=MissionProgressStatusEnum.DONE
    )
    await mission_progress_factory(
        user_multi, m_in_progress, status=MissionProgressStatusEnum.IN_PROGRESS
    )
    await mission_progress_factory(
        user_zero, m_idle, status=MissionProgressStatusEnum.IDLE
    )
    await mission_progress_factory(
        user_zero, m_in_progress, status=MissionProgressStatusEnum.IN_PROGRESS
    )
    multi_id, headers_multi = user_multi.usr_id, _auth_headers(user_multi)
    zero_id, headers_zero = user_zero.usr_id, _auth_headers(user_zero)
    await db_session.commit()

    async with _authenticated_http_client(
        db_session, test_app, monkeypatch
    ) as client:
        await _assert_xp_consistency(
            client,
            db_session,
            multi_id,
            headers_multi,
            expected_xp=200,
            expected_missions=2,
            expected_position=1,
        )
        await _assert_xp_consistency(
            client,
            db_session,
            zero_id,
            headers_zero,
            expected_xp=0,
            expected_missions=0,
            expected_position=2,
        )

        update_resp = await client.put(
            "/api/v1/users/me",
            json={"name": "Multi Atualizado"},
            headers=headers_multi,
        )
        assert update_resp.status_code == 200
        updated_profile = update_resp.json()
        assert updated_profile["name"] == "Multi Atualizado"
        assert updated_profile["xp"] == 200
        assert updated_profile["missionsCompleted"] == 2


@pytest.mark.anyio
async def test_recalculation_and_resubmission_are_idempotent(
    db_session,
    learning_hierarchy_factory,
    quiz_factory,
    mission_factory,
    test_app,
    monkeypatch,
):
    """Recalcular ou reenviar resposta em missão DONE não duplica XP."""
    hierarchy = await learning_hierarchy_factory()
    user = hierarchy.user
    quiz = await quiz_factory(hierarchy.lesson)
    await mission_factory(
        hierarchy.step,
        xp_reward=150,
        criteria="number_of_lessons_completed",
        criteria_value=1,
    )
    user_id, headers = user.usr_id, _auth_headers(user)
    quiz_id, step_id = quiz.qui_id, hierarchy.step.stp_id
    await db_session.commit()

    async with _authenticated_http_client(
        db_session, test_app, monkeypatch
    ) as client:
        first_submit = await client.post(
            f"/api/v1/quizzes/{quiz_id}/answers",
            json={"text": "Correta"},
            headers=headers,
        )
        assert first_submit.status_code == 201

        pos = await _assert_xp_consistency(
            client,
            db_session,
            user_id,
            headers,
            expected_xp=150,
            expected_missions=1,
        )

        recalc_url = f"/api/v1/steps/{step_id}/missions/recalculate-progress"
        recalc_first = await client.post(recalc_url, headers=headers)
        assert recalc_first.status_code == 204
        recalc_second = await client.post(recalc_url, headers=headers)
        assert recalc_second.status_code == 204

        repeat_submit = await client.post(
            f"/api/v1/quizzes/{quiz_id}/answers",
            json={"text": "Repetida"},
            headers=headers,
        )
        assert repeat_submit.status_code == 201

        await _assert_xp_consistency(
            client,
            db_session,
            user_id,
            headers,
            expected_xp=150,
            expected_missions=1,
            expected_position=pos,
        )


@pytest.mark.anyio
async def test_mission_soft_delete_excludes_xp_while_parent_delete_keeps_xp(
    db_session,
    learning_hierarchy_factory,
    step_factory,
    mission_factory,
    mission_progress_factory,
    user_factory,
    test_app,
    monkeypatch,
):
    """Soft delete da missão remove XP; soft delete de Step/Track preserva."""
    hierarchy_1 = await learning_hierarchy_factory()
    user_a = hierarchy_1.user
    step_1 = hierarchy_1.step
    step_2 = await step_factory(hierarchy_1.track, title="Etapa 2")

    mission_1 = await mission_factory(step_1, title="Missão 1", xp_reward=100)
    mission_2 = await mission_factory(step_2, title="Missão 2", xp_reward=250)

    hierarchy_2 = await learning_hierarchy_factory()
    mission_preserved = await mission_factory(
        hierarchy_2.step, title="Missão sob pai removido", xp_reward=180
    )
    user_c = hierarchy_2.user

    user_b = await user_factory(name="Competidor B")
    mission_b = await mission_factory(step_1, title="Missão B", xp_reward=120)

    await mission_progress_factory(
        user_a, mission_1, status=MissionProgressStatusEnum.DONE
    )
    await mission_progress_factory(
        user_a, mission_2, status=MissionProgressStatusEnum.DONE
    )
    await mission_progress_factory(
        user_b, mission_b, status=MissionProgressStatusEnum.DONE
    )
    await mission_progress_factory(
        user_c, mission_preserved, status=MissionProgressStatusEnum.DONE
    )
    user_a_id, headers_a = user_a.usr_id, _auth_headers(user_a)
    user_c_id, headers_c = user_c.usr_id, _auth_headers(user_c)
    mission_1_id, mission_2_id = mission_1.msn_id, mission_2.msn_id
    track_c_id, step_c_id = hierarchy_2.track.trk_id, hierarchy_2.step.stp_id
    await db_session.commit()

    async with _authenticated_http_client(
        db_session, test_app, monkeypatch
    ) as client:
        # Inicial: user_a (350 XP, pos 1), user_c (180 XP, pos 2),
        # user_b (120 XP, pos 3).
        await _assert_xp_consistency(
            client,
            db_session,
            user_a_id,
            headers_a,
            expected_xp=350,
            expected_missions=2,
            expected_position=1,
        )

        # Excluir mission_2 (250 XP) reduz user_a imediatamente para 100 XP.
        del_m2 = await client.delete(
            f"/api/v1/missions/{mission_2_id}",
            headers=headers_a,
        )
        assert del_m2.status_code == 204
        await _assert_xp_consistency(
            client,
            db_session,
            user_a_id,
            headers_a,
            expected_xp=100,
            expected_missions=1,
            expected_position=3,
        )

        # Excluir mission_1 zera o XP de user_a mantendo-o ativo no ranking.
        del_m1 = await client.delete(
            f"/api/v1/missions/{mission_1_id}",
            headers=headers_a,
        )
        assert del_m1.status_code == 204
        await _assert_xp_consistency(
            client,
            db_session,
            user_a_id,
            headers_a,
            expected_xp=0,
            expected_missions=0,
            expected_position=3,
        )

        # Excluir apenas Step e Track pai de mission_preserved mantém 180 XP.
        del_step = await client.delete(
            f"/api/v1/tracks/{track_c_id}/steps/{step_c_id}",
            headers=headers_c,
        )
        assert del_step.status_code == 204
        await _assert_xp_consistency(
            client,
            db_session,
            user_c_id,
            headers_c,
            expected_xp=180,
            expected_missions=1,
            expected_position=1,
        )

        del_track = await client.delete(
            f"/api/v1/tracks/{track_c_id}",
            headers=headers_c,
        )
        assert del_track.status_code == 204
        await _assert_xp_consistency(
            client,
            db_session,
            user_c_id,
            headers_c,
            expected_xp=180,
            expected_missions=1,
            expected_position=1,
        )
