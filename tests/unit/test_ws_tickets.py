import asyncio
from uuid import uuid4

from sidebrain_back.core.ws_tickets import WsTicketStore


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def set(self, key, value, *, ex, nx):
        assert ex == 60
        assert nx is True
        if key in self.values:
            return False
        self.values[key] = value
        return True

    async def getdel(self, key):
        return self.values.pop(key, None)


def test_ticket_is_bound_to_scope_and_consumed_once():
    async def scenario():
        store = WsTicketStore(FakeRedis())
        scope = {
            "user_id": str(uuid4()),
            "channel": "assessment",
            "resource_id": str(uuid4()),
        }
        ticket = await store.issue(scope)

        assert await store.consume(ticket) == scope
        assert await store.consume(ticket) is None

    asyncio.run(scenario())
