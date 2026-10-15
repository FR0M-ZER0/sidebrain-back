import asyncio

import pytest

from sidebrain_back.core.rate_limit import (
    AuthRateLimiter,
    RateLimitExceeded,
    RateLimitUnavailable,
)


class FakeRedis:
    def __init__(self):
        self.now = 1_000
        self.failures = {}
        self.locks = {}
        self.keys = []
        self.number_of_keys = []
        self.guard = asyncio.Lock()

    async def eval(self, script, number_of_keys, *args):
        failures_key, lock_key, sequence_key = args[:number_of_keys]
        self.number_of_keys.append(number_of_keys)
        self.keys.extend([failures_key, lock_key, sequence_key])
        async with self.guard:
            if "CHECK_RATE_LIMIT" in script:
                return max(0, self.locks.get(lock_key, 0) - self.now)
            if "RECORD_FAILURE" in script:
                retry = max(0, self.locks.get(lock_key, 0) - self.now)
                if retry:
                    return retry
                items = [
                    value
                    for value in self.failures.get(failures_key, [])
                    if value > self.now - 900
                ]
                items.append(self.now)
                self.failures[failures_key] = items
                if len(items) >= 5:
                    self.locks[lock_key] = self.now + 900
                return 0
            if "RECORD_SUCCESS" in script:
                retry = max(0, self.locks.get(lock_key, 0) - self.now)
                if retry:
                    return retry
                self.failures.pop(failures_key, None)
                return 0
            raise AssertionError("script desconhecido")


@pytest.mark.anyio
async def test_fifth_failure_arms_lock_and_sixth_attempt_is_blocked():
    redis = FakeRedis()
    limiter = AuthRateLimiter(redis)

    for _ in range(5):
        await limiter.check("login", "Pessoa@Example.com", "127.0.0.1")
        await limiter.record_failure(
            "login", "Pessoa@Example.com", "127.0.0.1"
        )

    with pytest.raises(RateLimitExceeded) as error:
        await limiter.check("login", "pessoa@example.com", "127.0.0.1")
    assert error.value.retry_after == 900
    assert all("pessoa@example.com" not in key for key in redis.keys)


@pytest.mark.anyio
async def test_success_resets_only_its_bucket_and_scopes_are_isolated():
    redis = FakeRedis()
    limiter = AuthRateLimiter(redis)

    await limiter.record_failure("login", "person@example.com", "origin-a")
    await limiter.record_failure("password", "user-id", "origin-a")
    await limiter.record_success("login", "person@example.com", "origin-a")

    assert len(redis.failures) == 1
    assert "password" in next(iter(redis.failures))


@pytest.mark.anyio
async def test_concurrent_failures_are_counted_atomically():
    redis = FakeRedis()
    limiter = AuthRateLimiter(redis)

    await asyncio.gather(
        *(
            limiter.record_failure("login", "person@example.com", "origin")
            for _ in range(5)
        )
    )

    with pytest.raises(RateLimitExceeded):
        await limiter.check("login", "person@example.com", "origin")

    assert all(number_of_keys == 3 for number_of_keys in redis.number_of_keys)
    assert any(key.endswith(":sequence") for key in redis.keys)


@pytest.mark.anyio
async def test_invalid_payload_does_not_count_when_limiter_is_not_called():
    redis = FakeRedis()
    AuthRateLimiter(redis)

    assert redis.failures == {}


@pytest.mark.anyio
async def test_redis_failure_closes_protected_operation():
    class BrokenRedis:
        async def eval(self, *_args):
            raise ConnectionError("redis indisponível")

    limiter = AuthRateLimiter(BrokenRedis())

    with pytest.raises(RateLimitUnavailable):
        await limiter.check("login", "person@example.com", "origin")
