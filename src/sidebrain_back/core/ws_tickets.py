import hashlib
import json
import secrets
from typing import Any

from redis.asyncio import Redis

from sidebrain_back.core.constants import Env

TICKET_TTL_SECONDS = 60


class WsTicketUnavailable(Exception):
    pass


class WsTicketStore:
    def __init__(self, client: Any) -> None:
        self.client = client

    async def issue(self, scope: dict[str, str]) -> str:
        try:
            for _attempt in range(3):
                ticket = secrets.token_urlsafe(32)
                created = await self.client.set(
                    self._key(ticket),
                    json.dumps(scope, separators=(",", ":")),
                    ex=TICKET_TTL_SECONDS,
                    nx=True,
                )
                if created:
                    return ticket
        except Exception as error:
            raise WsTicketUnavailable from error
        raise WsTicketUnavailable

    async def consume(self, ticket: str) -> dict[str, str] | None:
        try:
            raw = await self.client.getdel(self._key(ticket))
        except Exception as error:
            raise WsTicketUnavailable from error
        if raw is None:
            return None
        value = json.loads(raw)
        return value if isinstance(value, dict) else None

    @staticmethod
    def _key(ticket: str) -> str:
        digest = hashlib.sha256(ticket.encode()).hexdigest()
        return f"sidebrain:{Env.MODE}:ws-ticket:{digest}"


_redis_client: Redis | None = None


def get_ws_ticket_store() -> WsTicketStore:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(
            host=Env.REDIS_HOST,
            port=Env.REDIS_PORT,
            db=Env.REDIS_AUTH_DB,
            decode_responses=True,
        )
    return WsTicketStore(_redis_client)


async def close_ws_ticket_client() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
