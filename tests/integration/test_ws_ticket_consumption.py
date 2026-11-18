import asyncio

import pytest

from sidebrain_back.core.ws_tickets import (
    TICKET_TTL_SECONDS,
    close_ws_ticket_client,
    get_ws_ticket_store,
)


@pytest.mark.anyio
async def test_ticket_has_sixty_second_ttl_and_is_consumed_atomically():
    try:
        store = get_ws_ticket_store()
        scope = {
            "user_id": "owner",
            "channel": "step_preparation",
            "resource_id": "opaque-task-id",
        }
        ticket = await store.issue(scope)

        ttl = await store.client.ttl(store._key(ticket))
        assert 0 < ttl <= TICKET_TTL_SECONDS

        results = await asyncio.gather(
            store.consume(ticket),
            store.consume(ticket),
        )
        assert results.count(scope) == 1
        assert results.count(None) == 1
    finally:
        await close_ws_ticket_client()


@pytest.mark.anyio
async def test_invalid_or_already_consumed_ticket_is_absent():
    try:
        store = get_ws_ticket_store()
        assert await store.consume("ticket-that-does-not-exist") is None
    finally:
        await close_ws_ticket_client()
