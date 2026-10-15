from hashlib import sha256
from typing import Any

from redis.asyncio import Redis

from sidebrain_back.core.constants import Env

WINDOW_SECONDS = 15 * 60
BLOCK_SECONDS = 15 * 60
MAX_FAILURES = 5

CHECK_RATE_LIMIT_SCRIPT = """
-- CHECK_RATE_LIMIT
local ttl = redis.call('TTL', KEYS[2])
if ttl > 0 then return ttl end
return 0
"""

RECORD_FAILURE_SCRIPT = """
-- RECORD_FAILURE
local lock_ttl = redis.call('TTL', KEYS[2])
if lock_ttl > 0 then return lock_ttl end
local current_time = redis.call('TIME')
local now_ms = current_time[1] * 1000 + math.floor(current_time[2] / 1000)
local window_ms = tonumber(ARGV[1]) * 1000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now_ms - window_ms)
local member = tostring(now_ms) .. ':' .. tostring(current_time[2])
redis.call('ZADD', KEYS[1], now_ms, member)
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]))
local failures = redis.call('ZCARD', KEYS[1])
if failures >= tonumber(ARGV[2]) then
    redis.call('SET', KEYS[2], '1', 'EX', tonumber(ARGV[3]))
end
return 0
"""

RECORD_SUCCESS_SCRIPT = """
-- RECORD_SUCCESS
local ttl = redis.call('TTL', KEYS[2])
if ttl > 0 then return ttl end
redis.call('DEL', KEYS[1])
return 0
"""


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = max(1, retry_after)
        super().__init__("Limite de tentativas excedido.")


class RateLimitUnavailable(Exception):
    pass


class AuthRateLimiter:
    def __init__(self, client: Any) -> None:
        self.client = client

    async def check(self, scope: str, subject: str, origin: str) -> None:
        failures_key, lock_key = self._keys(scope, subject, origin)
        retry_after = await self._eval(
            CHECK_RATE_LIMIT_SCRIPT,
            failures_key,
            lock_key,
        )
        if retry_after > 0:
            raise RateLimitExceeded(retry_after)

    async def record_failure(
        self,
        scope: str,
        subject: str,
        origin: str,
    ) -> None:
        failures_key, lock_key = self._keys(scope, subject, origin)
        retry_after = await self._eval(
            RECORD_FAILURE_SCRIPT,
            failures_key,
            lock_key,
            WINDOW_SECONDS,
            MAX_FAILURES,
            BLOCK_SECONDS,
        )
        if retry_after > 0:
            raise RateLimitExceeded(retry_after)

    async def record_success(
        self,
        scope: str,
        subject: str,
        origin: str,
    ) -> None:
        failures_key, lock_key = self._keys(scope, subject, origin)
        retry_after = await self._eval(
            RECORD_SUCCESS_SCRIPT,
            failures_key,
            lock_key,
        )
        if retry_after > 0:
            raise RateLimitExceeded(retry_after)

    async def _eval(self, script: str, *arguments: Any) -> int:
        try:
            result = await self.client.eval(script, 2, *arguments)
            return int(result)
        except RateLimitExceeded:
            raise
        except Exception as error:
            raise RateLimitUnavailable(
                "O limitador de tentativas está indisponível."
            ) from error

    @staticmethod
    def _keys(scope: str, subject: str, origin: str) -> tuple[str, str]:
        normalized_subject = (
            subject.strip().lower() if scope == "login" else subject
        )
        digest = sha256(
            f"{scope}\0{normalized_subject}\0{origin}".encode()
        ).hexdigest()
        prefix = f"sidebrain:auth:{scope}:{digest}"
        return f"{prefix}:failures", f"{prefix}:lock"


_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(
            host=Env.REDIS_HOST,
            port=Env.REDIS_PORT,
            db=Env.REDIS_AUTH_DB,
            decode_responses=True,
        )
    return _redis_client


def get_auth_rate_limiter() -> AuthRateLimiter:
    return AuthRateLimiter(get_redis_client())


async def close_rate_limit_client() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
