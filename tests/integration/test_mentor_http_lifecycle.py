from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import func, select

from main import app
from sidebrain_back.core.database import get_db
from sidebrain_back.models.mentor_generation_model import MentorSendReservation
from sidebrain_back.models.mentor_message_model import MentorMessage
from sidebrain_back.repositories.mentor_generation_repository import (
    MentorGenerationRepository,
)
from sidebrain_back.routers.v1.auth_router import get_current_user
from sidebrain_back.services.mentor_processing_service import (
    MentorProcessingService,
)


@pytest.mark.anyio
async def test_mentor_http_lifecycle_with_controlled_provider(
    db_session, learning_hierarchy_factory, user_factory
):
    hierarchy = await learning_hierarchy_factory()
    other = await user_factory()
    user_id = hierarchy.user.usr_id
    track_id = hierarchy.track.trk_id
    other_id = other.usr_id

    async def override_db():
        yield db_session

    async def override_user():
        return SimpleNamespace(usr_id=user_id)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            notice = (await client.get("/api/v1/mentor-consent")).json()
            created = await client.post(
                "/api/v1/mentor-conversations",
                json={"track_id": str(track_id)},
            )
            assert created.status_code == 201
            conversation_id = created.json()["id"]
            base = f"/api/v1/mentor-conversations/{conversation_id}"

            async def override_other():
                return SimpleNamespace(usr_id=other_id)

            app.dependency_overrides[get_current_user] = override_other
            assert (await client.get(base)).status_code == 404
            foreign_track = await client.post(
                "/api/v1/mentor-conversations",
                json={"track_id": str(track_id)},
            )
            assert foreign_track.status_code == 404
            foreign_submission = await client.post(
                f"{base}/messages",
                json={"content": "Dado de terceiro"},
                headers={"Idempotency-Key": str(uuid4())},
            )
            assert foreign_submission.status_code == 404
            app.dependency_overrides[get_current_user] = override_user
            key = str(uuid4())
            request = {"content": "Como estudar?"}
            blocked = await client.post(
                f"{base}/messages",
                json=request,
                headers={"Idempotency-Key": key},
            )
            assert blocked.status_code == 403
            accepted = await client.put(
                "/api/v1/mentor-consent",
                json={
                    "notice_version": notice["notice_version"],
                    "accepted": True,
                },
            )
            assert accepted.status_code == 200
            submitted = await client.post(
                f"{base}/messages",
                json=request,
                headers={"Idempotency-Key": key},
            )
            assert submitted.status_code == 202
            generation_id = submitted.json()["generation_id"]
            generator = Mock()
            generator.generate_mentor_response = AsyncMock()
            captured = {}

            async def generate(message, get_tool_data, *, history):
                captured["message"] = message
                captured["automatic_history"] = history
                captured["history"] = await get_tool_data(
                    "consultar_historico"
                )
                return "Revise os fundamentos."

            generator.generate_mentor_response.side_effect = generate
            await MentorProcessingService(db_session, generator).process(
                user_id, UUID(generation_id)
            )
            status = await client.get(f"{base}/generations/{generation_id}")
            assert status.json()["status"] == "completed"
            message_id = status.json()["response_message_id"]
            message = await client.get(f"{base}/messages/{message_id}")
            assert message.json()["content"] == "Revise os fundamentos."
            events_url = f"{base}/generations/{generation_id}/events"
            stream = await client.get(events_url)
            assert stream.status_code == 200
            assert '"content":"Revise os fundamentos."' in stream.text
            app.dependency_overrides[get_current_user] = override_other
            assert (await client.get(events_url)).status_code == 404
            app.dependency_overrides[get_current_user] = override_user
            replay = await client.post(
                f"{base}/messages",
                json=request,
                headers={"Idempotency-Key": key},
            )
            assert replay.json()["generation_id"] == generation_id
            assert replay.json()["status"] == "completed"
            failed_submission = await client.post(
                f"{base}/messages",
                json={"content": "Tenho pouco tempo."},
                headers={"Idempotency-Key": str(uuid4())},
            )
            failed_id = failed_submission.json()["generation_id"]
            failing_generator = Mock()
            failing_generator.generate_mentor_response = AsyncMock()
            failing_generator.generate_mentor_response.side_effect = (
                ValueError("inválido")
            )
            await MentorProcessingService(
                db_session, failing_generator
            ).process(user_id, UUID(failed_id))
            failed = await client.get(f"{base}/generations/{failed_id}")
            assert failed.json()["status"] == "failed"
            retry_key = str(uuid4())
            retry_url = f"{base}/generations/{failed_id}/retry"
            retry = await client.post(
                retry_url, headers={"Idempotency-Key": retry_key}
            )
            assert retry.status_code == 202
            retry_id = retry.json()["generation_id"]
            assert (
                retry.json()["message_id"]
                == (failed_submission.json()["message_id"])
            )
            repeated_retry = await client.post(
                retry_url, headers={"Idempotency-Key": retry_key}
            )
            assert repeated_retry.json()["generation_id"] == retry_id
            await MentorProcessingService(db_session, generator).process(
                user_id, UUID(retry_id)
            )
            assert captured["message"] == "Tenho pouco tempo."
            assert captured["automatic_history"] == [
                {"role": "student", "content": "Como estudar?"},
                {"role": "mentor", "content": "Revise os fundamentos."},
            ]
            context = captured["history"]
            assert any(
                item["content"] == "Como estudar?"
                for item in context["historico"]
            )
            history = await client.get(f"{base}/messages")
            assert history.json()["total_items"] == 4
            deleted = await client.delete(base)
            assert deleted.status_code == 204
            assert (await client.get(base)).status_code == 404
            count = await db_session.scalar(
                select(func.count())
                .select_from(MentorMessage)
                .where(MentorMessage.conversation_id == UUID(conversation_id))
            )
            assert count == 0
            await MentorProcessingService(db_session, generator).process(
                user_id, UUID(generation_id)
            )
            assert generator.generate_mentor_response.call_count == 2
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.anyio
async def test_deletion_returns_503_when_send_is_inconclusive(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    track_id = hierarchy.track.trk_id

    async def override_db():
        yield db_session

    async def override_user():
        return SimpleNamespace(usr_id=user_id)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            notice = (await client.get("/api/v1/mentor-consent")).json()
            await client.put(
                "/api/v1/mentor-consent",
                json={
                    "notice_version": notice["notice_version"],
                    "accepted": True,
                },
            )
            created = await client.post(
                "/api/v1/mentor-conversations",
                json={"track_id": str(track_id)},
            )
            base = f"/api/v1/mentor-conversations/{created.json()['id']}"
            submitted = await client.post(
                f"{base}/messages",
                json={"content": "Como estudar?"},
                headers={"Idempotency-Key": str(uuid4())},
            )
            reservation = await MentorGenerationRepository(db_session).reserve(
                user_id,
                UUID(submitted.json()["generation_id"]),
                notice["notice_version"],
            )
            reservation_id = reservation.id
            await db_session.commit()
            revoked = await client.delete("/api/v1/mentor-consent")
            assert revoked.status_code == 503
            blocked = await client.delete(base)
            assert blocked.status_code == 503
            assert (await client.get(base)).status_code == 200
            reservation = await db_session.get(
                MentorSendReservation, reservation_id
            )
            assert reservation.status == "in_flight"
            reservation.status = "finished"
            await db_session.commit()
            revoked = await client.delete("/api/v1/mentor-consent")
            assert revoked.status_code == 204
            assert (await client.delete(base)).status_code == 204
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.anyio
async def test_http_context_requires_matching_lesson_and_is_idempotent(
    db_session, learning_hierarchy_factory, quiz_factory
):
    own = await learning_hierarchy_factory()
    foreign = await learning_hierarchy_factory()
    quiz = await quiz_factory(own.lesson)
    user_id = own.user.usr_id
    track_id, lesson_id = own.track.trk_id, own.lesson.lsn_id
    foreign_lesson_id, quiz_id = foreign.lesson.lsn_id, quiz.qui_id

    async def override_db():
        yield db_session

    async def override_user():
        return SimpleNamespace(usr_id=user_id)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            notice = (await client.get("/api/v1/mentor-consent")).json()
            await client.put(
                "/api/v1/mentor-consent",
                json={
                    "notice_version": notice["notice_version"],
                    "accepted": True,
                },
            )
            created = await client.post(
                "/api/v1/mentor-conversations",
                json={"track_id": str(track_id)},
            )
            base = (
                f"/api/v1/mentor-conversations/{created.json()['id']}/messages"
            )
            key = str(uuid4())
            payload = {
                "content": "Poderia me ajudar?",
                "context": {
                    "type": "quiz",
                    "lesson_id": str(lesson_id),
                    "quiz_id": str(quiz_id),
                },
            }
            submitted = await client.post(
                base, json=payload, headers={"Idempotency-Key": key}
            )
            assert submitted.status_code == 202
            replay = await client.post(
                base, json=payload, headers={"Idempotency-Key": key}
            )
            assert (
                replay.json()["generation_id"]
                == submitted.json()["generation_id"]
            )
            changed = {
                "content": payload["content"],
                "context": {"type": "lesson", "lesson_id": str(lesson_id)},
            }
            conflict = await client.post(
                base, json=changed, headers={"Idempotency-Key": key}
            )
            assert conflict.status_code == 409
            invalid = {
                "content": "Ajude",
                "context": {
                    "type": "lesson",
                    "lesson_id": str(foreign_lesson_id),
                },
            }
            denied = await client.post(
                base,
                json=invalid,
                headers={"Idempotency-Key": str(uuid4())},
            )
            assert denied.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
