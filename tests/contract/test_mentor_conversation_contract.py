from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from sidebrain_back.schemas.mentor_schema import (
    MentorConversationResponse,
    MentorMessageResponse,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.services.mentor_consent_service import (
    MentorConsentUnavailable,
)
from sidebrain_back.services.mentor_service import (
    MentorNotFound,
    get_mentor_service,
)

BASE = "/api/v1/mentor-conversations"


def test_mentor_openapi_tag(test_app):
    paths = test_app.openapi()["paths"]
    mentor_operations = [
        operation
        for path, methods in paths.items()
        if path.startswith(
            ("/api/v1/mentor-conversations", "/api/v1/mentor-consent")
        )
        for operation in methods.values()
    ]
    assert mentor_operations
    assert all(
        operation["tags"] == ["Mentor"] for operation in mentor_operations
    )


class FakeConversationService:
    def __init__(self):
        self.blocked = False

    async def list_mentor_conversations(self, _user, page, size, _track):
        now = datetime.now(UTC)
        value = MentorConversationResponse(
            id=uuid4(), track_id=uuid4(), created_at=now, updated_at=now
        )
        return PaginatedResponse.build([value], page, size, 1)

    async def list_mentor_messages(self, _user, _conversation, page, size):
        now = datetime.now(UTC)
        messages = [
            MentorMessageResponse(
                id=uuid4(),
                sequence=1,
                role="student",
                content="Oi",
                created_at=now,
            ),
            MentorMessageResponse(
                id=uuid4(),
                sequence=2,
                role="mentor",
                content="Olá",
                created_at=now,
            ),
        ]
        return PaginatedResponse.build(messages, page, size, 2)

    async def get_mentor_conversation(self, *_args):
        raise MentorNotFound("Conversa não encontrada.")

    async def delete_mentor_conversations(self, *_args):
        if self.blocked:
            raise MentorConsentUnavailable("Envio inconclusivo.")


def test_conversation_listing_and_deletion_contract(test_app):
    service = FakeConversationService()
    test_app.dependency_overrides[get_mentor_service] = lambda: service
    try:
        with TestClient(test_app) as client:
            listing = client.get(BASE, params={"page": 1, "page_size": 20})
            assert listing.status_code == 200
            assert listing.json()["total_items"] == 1
            conversation = uuid4()
            messages = client.get(f"{BASE}/{conversation}/messages")
            assert messages.status_code == 200
            assert [item["sequence"] for item in messages.json()["data"]] == [
                1,
                2,
            ]
            assert client.get(f"{BASE}/{conversation}").status_code == 404
            service.blocked = True
            assert client.delete(f"{BASE}/{conversation}").status_code == 503
            service.blocked = False
            assert client.delete(f"{BASE}/{conversation}").status_code == 204
            assert client.delete(BASE).status_code == 204
    finally:
        test_app.dependency_overrides.pop(get_mentor_service, None)
