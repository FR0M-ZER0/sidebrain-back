import asyncio
import os
from math import ceil
from time import perf_counter
from uuid import uuid4

import httpx
import pytest

CLIENTS = 20
MAX_P95_SECONDS = 2.0


@pytest.mark.anyio
async def test_auth_profile_p95_with_twenty_concurrent_clients(
    record_property,
):
    base_url = os.getenv("AUTH_PERFORMANCE_BASE_URL")
    if not base_url:
        pytest.skip(
            "Defina AUTH_PERFORMANCE_BASE_URL para medir o ambiente alvo."
        )

    timings: list[float] = []

    async def journey(client_number: int) -> None:
        email = f"perf-{client_number}-{uuid4()}@example.com"
        password = "senha-performance-123"
        async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:
            started = perf_counter()
            registration = await client.post(
                "/api/v1/auth/register",
                json={
                    "name": f"Performance {client_number}",
                    "email": email,
                    "password": password,
                },
            )
            timings.append(perf_counter() - started)
            registration.raise_for_status()

            started = perf_counter()
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            timings.append(perf_counter() - started)
            login.raise_for_status()
            token = login.json()["accessToken"]
            headers = {"Authorization": f"Bearer {token}"}

            started = perf_counter()
            profile = await client.get("/api/v1/users/me", headers=headers)
            timings.append(perf_counter() - started)
            profile.raise_for_status()
            await client.delete("/api/v1/users/me", headers=headers)

    await asyncio.gather(*(journey(index) for index in range(CLIENTS)))
    percentile_index = ceil(0.95 * len(timings)) - 1
    p95 = sorted(timings)[percentile_index]
    record_property("auth_profile_p95_seconds", p95)
    assert p95 <= MAX_P95_SECONDS
