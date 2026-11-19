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
async def test_user_statistics_p95_with_twenty_concurrent_clients(
    record_property,
):
    base_url = os.getenv("AUTH_PERFORMANCE_BASE_URL")
    if not base_url:
        pytest.skip(
            "Defina AUTH_PERFORMANCE_BASE_URL para medir o ambiente alvo."
        )

    timings: list[float] = []

    async def journey(client_number: int) -> None:
        email = f"stats-perf-{client_number}-{uuid4()}@example.com"
        password = "senha-performance-123"
        async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:
            registration = await client.post(
                "/api/v1/auth/register",
                json={
                    "name": f"Statistics Performance {client_number}",
                    "email": email,
                    "password": password,
                },
            )
            registration.raise_for_status()

            login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            login.raise_for_status()
            headers = {
                "Authorization": f"Bearer {login.json()['accessToken']}"
            }

            started = perf_counter()
            statistics = await client.get(
                "/api/v1/users/me/statistics", headers=headers
            )
            timings.append(perf_counter() - started)
            statistics.raise_for_status()
            await client.delete("/api/v1/users/me", headers=headers)

    await asyncio.gather(*(journey(index) for index in range(CLIENTS)))
    percentile_index = ceil(0.95 * len(timings)) - 1
    p95 = sorted(timings)[percentile_index]
    record_property("user_statistics_p95_seconds", p95)
    assert p95 <= MAX_P95_SECONDS
