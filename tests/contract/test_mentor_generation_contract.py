import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from sidebrain_back.schemas.mentor_schema import (
    MentorConversationResponse,
    MentorGenerationAccepted,
    MentorGenerationEvent,
    MentorGenerationResponse,
    MentorMessageResponse,
)
from sidebrain_back.services.mentor_service import (
    MentorConsentRequired,
    MentorNotFound,
    get_mentor_service,
)

BASE = "/api/v1/mentor-conversations"


class FakeMentorService:
    async def create_mentor_conversation(self, _user_id, track_id):
        now = datetime.now(UTC)
        return MentorConversationResponse(
            id=uuid4(), track_id=track_id, created_at=now, updated_at=now
        )

    async def create_mentor_message(self, _user, _conversation, _key, payload):
        if payload.content == "sem autorização":
            raise MentorConsentRequired("Autorização necessária.")
        return MentorGenerationAccepted(
            generation_id=uuid4(), message_id=uuid4(), status="queued"
        )

    async def get_mentor_message(self, *_args):
        raise MentorNotFound("Mensagem não encontrada.")

    async def get_mentor_generation(
        self, _user_id, _conversation_id, generation_id
    ):
        return MentorGenerationResponse(
            id=generation_id,
            message_id=uuid4(),
            status="failed",
            response_message_id=None,
            error_code="generation_failed",
        )

    async def retry_mentor_generation(self, *_args):
        return MentorGenerationAccepted(
            generation_id=uuid4(), message_id=uuid4(), status="queued"
        )


def test_mentor_endpoints_require_authentication():
    with TestClient(app) as client:
        response = client.get(BASE)
        stream = client.get(f"{BASE}/{uuid4()}/generations/{uuid4()}/events")
    assert response.status_code == 401
    assert stream.status_code == 401


def test_mentor_generation_events(test_app, monkeypatch):
    generation_id, message_id = uuid4(), uuid4()
    statuses = iter(["queued", "processing", "completed"])

    class StreamingService(FakeMentorService):
        async def get_mentor_generation_event(self, *_args):
            status = next(statuses)
            message = None
            if status == "completed":
                message = MentorMessageResponse(
                    id=message_id,
                    sequence=2,
                    role="mentor",
                    content="Revise os fundamentos.",
                    created_at=datetime.now(UTC),
                )
            return MentorGenerationEvent(
                generation=MentorGenerationResponse(
                    id=generation_id,
                    message_id=uuid4(),
                    status=status,
                    response_message_id=message_id if message else None,
                    error_code=None,
                ),
                message=message,
            )

    async def no_wait(_seconds):
        pass

    monkeypatch.setattr(
        "sidebrain_back.routers.v1.mentor_router.asyncio.sleep", no_wait
    )
    test_app.dependency_overrides[get_mentor_service] = StreamingService
    try:
        with TestClient(test_app) as client:
            response = client.get(
                f"{BASE}/{uuid4()}/generations/{generation_id}/events"
            )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        events = response.text.strip().split("\n\n")
        data = [json.loads(event.split("\ndata: ")[1]) for event in events]
        assert [item["generation"]["status"] for item in data] == [
            "queued",
            "processing",
            "completed",
        ]
        assert data[-1]["message"]["content"] == "Revise os fundamentos."
    finally:
        test_app.dependency_overrides.pop(get_mentor_service, None)


def test_mentor_generation_events_not_found(test_app):
    class MissingService(FakeMentorService):
        async def get_mentor_generation_event(self, *_args):
            raise MentorNotFound("Geração não encontrada.")

    test_app.dependency_overrides[get_mentor_service] = MissingService
    try:
        with TestClient(test_app) as client:
            response = client.get(
                f"{BASE}/{uuid4()}/generations/{uuid4()}/events"
            )
        assert response.status_code == 404
    finally:
        test_app.dependency_overrides.pop(get_mentor_service, None)


def test_mentor_generation_events_failed_and_reconnect(test_app):
    generation_id = uuid4()

    class FailedService(FakeMentorService):
        async def get_mentor_generation_event(self, *_args):
            return MentorGenerationEvent(
                generation=await self.get_mentor_generation(
                    None, None, generation_id
                )
            )

    test_app.dependency_overrides[get_mentor_service] = FailedService
    try:
        with TestClient(test_app) as client:
            url = f"{BASE}/{uuid4()}/generations/{generation_id}/events"
            for _ in range(2):
                response = client.get(url)
                assert response.status_code == 200
                assert response.text.count("event: generation") == 1
                data = json.loads(response.text.split("\ndata: ")[1])
                assert data["generation"]["status"] == "failed"
                assert data["message"] is None
    finally:
        test_app.dependency_overrides.pop(get_mentor_service, None)


def test_mentor_generation_http_contract(test_app):
    test_app.dependency_overrides[get_mentor_service] = lambda: (
        FakeMentorService()
    )
    try:
        with TestClient(test_app) as client:
            created = client.post(BASE, json={"track_id": str(uuid4())})
            assert created.status_code == 201
            conversation_id = created.json()["id"]
            url = f"{BASE}/{conversation_id}/messages"
            missing_key = client.post(url, json={"content": "Ajuda"})
            assert missing_key.status_code == 422
            headers = {"Idempotency-Key": str(uuid4())}
            invalid = client.post(url, json={"content": "  "}, headers=headers)
            assert invalid.status_code == 422
            forbidden = client.post(
                url, json={"content": "sem autorização"}, headers=headers
            )
            assert forbidden.status_code == 403
            assert forbidden.headers["content-type"].startswith(
                "application/problem+json"
            )
            accepted = client.post(
                url, json={"content": "Ajuda"}, headers=headers
            )
            assert accepted.status_code == 202
            assert accepted.json()["status"] == "queued"
            missing = client.get(f"{url}/{uuid4()}")
            assert missing.status_code == 404
            generation_id = uuid4()
            generation_url = (
                f"{BASE}/{conversation_id}/generations/{generation_id}"
            )
            status = client.get(generation_url)
            assert status.status_code == 200
            assert status.json()["status"] == "failed"
            retry = client.post(f"{generation_url}/retry", headers=headers)
            assert retry.status_code == 202
            assert retry.json()["status"] == "queued"
    finally:
        test_app.dependency_overrides.pop(get_mentor_service, None)
