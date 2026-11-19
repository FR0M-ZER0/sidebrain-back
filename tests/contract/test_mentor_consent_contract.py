from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from main import app
from sidebrain_back.schemas.mentor_consent_schema import MentorConsentResponse
from sidebrain_back.services.auth_errors import ConflictError
from sidebrain_back.services.mentor_consent_service import (
    MentorConsentUnavailable,
    get_mentor_consent_service,
)

URL = "/api/v1/mentor-consent"


class FakeConsentService:
    def __init__(self):
        self.granted_at = None

    async def get_mentor_consent(self, _user_id):
        return MentorConsentResponse(
            notice_version="1",
            purpose="Mentoria",
            recipient="Provedor de teste",
            data_categories=["mensagens"],
            retention_notice="A retenção depende do provedor.",
            authorized=self.granted_at is not None,
            granted_at=self.granted_at,
        )

    async def accept_mentor_consent(self, user_id, notice_version):
        if notice_version != "1":
            raise ConflictError("Versão desatualizada")
        self.granted_at = datetime.now(UTC)
        return await self.get_mentor_consent(user_id)

    async def revoke_mentor_consent(self, _user_id):
        self.granted_at = None


@pytest.fixture
def consent_app(test_app):
    service = FakeConsentService()
    test_app.dependency_overrides[get_mentor_consent_service] = lambda: service
    return test_app


def test_consent_requires_authentication():
    with TestClient(app) as client:
        response = client.get(URL)

    assert response.status_code == 401
    assert response.headers["content-type"].startswith(
        "application/problem+json"
    )


def test_consent_notice_and_explicit_acceptance(consent_app):
    with TestClient(consent_app) as client:
        notice = client.get(URL)
        assert notice.status_code == 200
        body = notice.json()
        assert body["authorized"] is False
        assert body["notice_version"]
        assert body["purpose"]
        assert body["recipient"]
        assert body["data_categories"]
        assert body["retention_notice"]
        assert body["granted_at"] is None

        accepted = client.put(
            URL,
            json={"notice_version": body["notice_version"], "accepted": True},
        )
        assert accepted.status_code == 200
        assert accepted.json()["authorized"] is True
        assert accepted.json()["granted_at"] is not None

        current = client.get(URL)
        assert current.status_code == 200
        assert current.json()["authorized"] is True

        revoked = client.delete(URL)
        assert revoked.status_code == 204
        assert not revoked.content
        assert client.get(URL).json()["authorized"] is False
        assert client.delete(URL).status_code == 204


def test_consent_rejects_implicit_or_outdated_acceptance(consent_app):
    with TestClient(consent_app) as client:
        notice = client.get(URL)
        assert notice.status_code == 200
        version = notice.json()["notice_version"]

        rejected = client.put(
            URL, json={"notice_version": version, "accepted": False}
        )
        assert rejected.status_code == 422
        assert rejected.headers["content-type"].startswith(
            "application/problem+json"
        )

        missing = client.put(URL, json={"notice_version": version})
        assert missing.status_code == 422

        outdated = client.put(
            URL, json={"notice_version": "obsolete-version", "accepted": True}
        )
        assert outdated.status_code == 409
        assert outdated.headers["content-type"].startswith(
            "application/problem+json"
        )
        assert client.get(URL).json()["authorized"] is False


def test_revocation_reports_inconclusive_send(consent_app):
    service = consent_app.dependency_overrides[get_mentor_consent_service]()

    async def revoke_with_inflight(_user_id):
        raise MentorConsentUnavailable("Envio inconclusivo.")

    service.revoke_mentor_consent = revoke_with_inflight
    with TestClient(consent_app) as client:
        response = client.delete(URL)

    assert response.status_code == 503
    assert response.headers["content-type"].startswith(
        "application/problem+json"
    )
