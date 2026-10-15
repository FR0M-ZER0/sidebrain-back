import os
from dataclasses import dataclass
from uuid import uuid4

import httpx
import pytest


@dataclass(frozen=True)
class Consumer:
    identifier: str
    name: str
    email_prefix: str


CONSUMERS = (
    Consumer("consumer-01", "Consumidor Web", "web"),
    Consumer("consumer-02", "Consumidor Mobile", "mobile"),
    Consumer("consumer-03", "Consumidor CLI", "cli"),
    Consumer("consumer-04", "Integracao Parceira A", "partner-a"),
    Consumer("consumer-05", "Integracao Parceira B", "partner-b"),
)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "consumer",
    CONSUMERS,
    ids=lambda consumer: consumer.identifier,
)
async def test_consumer_completes_public_auth_journey(
    consumer: Consumer,
) -> None:
    base_url = os.getenv("AUTH_CONSUMER_BASE_URL")
    if not base_url:
        pytest.skip(
            "Defina AUTH_CONSUMER_BASE_URL para validar consumidores HTTP."
        )

    suffix = uuid4().hex
    email = f"{consumer.email_prefix}-{suffix}@example.com"
    password = f"Contrato-{suffix[:12]}"

    async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:
        registration = await client.post(
            "/api/v1/auth/register",
            json={
                "name": consumer.name,
                "email": email,
                "password": password,
            },
        )
        assert registration.status_code == 201
        registration_body = registration.json()
        assert set(registration_body) == {"accessToken", "tokenType", "user"}
        assert set(registration_body["user"]) == {"id", "name", "email"}
        assert registration_body["tokenType"] == "Bearer"

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200
        login_body = login.json()
        assert set(login_body) == {"accessToken", "tokenType", "user"}
        assert login_body["user"] == registration_body["user"]

        headers = {"Authorization": f"Bearer {login_body['accessToken']}"}
        profile = await client.get("/api/v1/users/me", headers=headers)
        assert profile.status_code == 200
        assert profile.json() == registration_body["user"]

        cleanup = await client.delete("/api/v1/users/me", headers=headers)
        assert cleanup.status_code == 204
        assert cleanup.content == b""
