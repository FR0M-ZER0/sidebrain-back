import asyncio
import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from sidebrain_back.core.database import engine


def _lock_key(user_id: UUID) -> int:
    digest = hashlib.blake2b(
        user_id.bytes, digest_size=8, person=b"mentor-lock"
    ).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


@asynccontextmanager
async def mentor_user_lock(
    user_id: UUID, *, wait_seconds: float = 5.0
) -> AsyncIterator[AsyncConnection]:
    """Hold a PostgreSQL session lock without a transaction during I/O."""
    key = _lock_key(user_id)
    acquired = False
    deadline = asyncio.get_running_loop().time() + wait_seconds
    async with engine.connect() as connection:
        await connection.execution_options(isolation_level="AUTOCOMMIT")
        try:
            while not acquired:
                result = await connection.execute(
                    text("SELECT pg_try_advisory_lock(:key)"), {"key": key}
                )
                acquired = bool(result.scalar_one())
                if acquired:
                    break
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise TimeoutError("Bloqueio de mentoria indisponível")
                await asyncio.sleep(min(0.05, remaining))
            yield connection
        finally:
            if acquired and connection.invalidated:
                raise RuntimeError("Conexão do bloqueio de mentoria perdida")
            if acquired:
                try:
                    result = await connection.execute(
                        text("SELECT pg_advisory_unlock(:key)"), {"key": key}
                    )
                    if not result.scalar_one():
                        await connection.invalidate()
                        raise RuntimeError("Bloqueio de mentoria perdido")
                except BaseException:
                    await connection.invalidate()
                    raise
