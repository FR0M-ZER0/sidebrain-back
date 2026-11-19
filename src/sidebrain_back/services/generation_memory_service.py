import asyncio
import logging
from collections.abc import Callable
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.constants import Env
from sidebrain_back.repositories.generation_cache_repository import (
    GenerationCacheRepository,
)
from sidebrain_back.repositories.topic_alias_repository import (
    TopicAliasRepository,
)
from sidebrain_back.services.ai_memory_service import AIMemoryService

logger = logging.getLogger(__name__)
Payload = TypeVar("Payload", bound=BaseModel)


class GenerationMemoryService:
    """Reutiliza artefatos globais sem compartilhar instâncias de usuários."""

    def __init__(self, db: AsyncSession, cache: GenerationCacheRepository):
        self.db = db
        self.cache = cache

    async def generate(
        self,
        *,
        content_type: str,
        context: dict,
        topic_field: str,
        schema: type[Payload],
        generator: Callable[[], Payload],
    ) -> tuple[Payload, str, object | None]:
        if not Env.AI_MEMORY_ENABLED:
            await self.db.rollback()
            return schema.model_validate(generator()), "ai", None

        owner = uuid4().hex
        acquired = False
        fingerprint = None
        redis = None
        redis_acquired = False
        try:
            memory = AIMemoryService(TopicAliasRepository(self.db))
            context = dict(context)
            context[topic_field] = await memory.canonicalize_topic(
                context[topic_field]
            )
            fingerprint, envelope = memory.fingerprint(
                content_type=content_type, canonical_context=context
            )
            await self.db.rollback()
            if Env.AI_MEMORY_REDIS_LOCK_ENABLED:
                redis = Redis(
                    host=Env.REDIS_HOST,
                    port=Env.REDIS_PORT,
                    socket_connect_timeout=0.2,
                    socket_timeout=0.2,
                )
                try:
                    for attempt in range(5):
                        redis_acquired = bool(
                            await redis.set(
                                f"ai-memory:{content_type}:{fingerprint}",
                                owner,
                                nx=True,
                                ex=max(1, Env.AI_MEMORY_LEASE_SECONDS),
                            )
                        )
                        if redis_acquired:
                            break
                        if attempt < 4:
                            await asyncio.sleep(0.05)
                except Exception:
                    logger.warning("Lock Redis indisponível.")

            cache = await self.cache.get_ready(fingerprint, content_type)
            if cache is not None and cache.payload is not None:
                result = schema.model_validate(cache.payload)
                cache_id = cache.id
                await self.db.rollback()
                return result, "cache", cache_id
            cache, acquired = await self.cache.reserve(
                fingerprint=fingerprint,
                content_type=content_type,
                fingerprint_version=envelope["fingerprint_version"],
                prompt_version=envelope["prompt_version"],
                provider=envelope["provider"],
                model=envelope["model"],
                canonical_context=envelope["canonical_context"],
                lease_owner=owner,
                lease_seconds=Env.AI_MEMORY_LEASE_SECONDS,
            )
            await self.db.commit()
            if not acquired:
                cache = await self.cache.wait_for_ready(
                    fingerprint,
                    content_type,
                    timeout_seconds=Env.AI_MEMORY_LEASE_SECONDS,
                )
                if cache is not None and cache.payload is not None:
                    result = schema.model_validate(cache.payload)
                    cache_id = cache.id
                    await self.db.rollback()
                    return result, "cache", cache_id
                cache, acquired = await self.cache.reserve(
                    fingerprint=fingerprint,
                    content_type=content_type,
                    fingerprint_version=envelope["fingerprint_version"],
                    prompt_version=envelope["prompt_version"],
                    provider=envelope["provider"],
                    model=envelope["model"],
                    canonical_context=envelope["canonical_context"],
                    lease_owner=owner,
                    lease_seconds=Env.AI_MEMORY_LEASE_SECONDS,
                )
                await self.db.commit()
        except Exception:
            logger.warning("Memória de IA indisponível; geração sem cache.")
            await self.db.rollback()
            acquired = False
        finally:
            if redis is not None:
                if redis_acquired:
                    try:
                        await redis.eval(
                            "if redis.call('get', KEYS[1]) == ARGV[1] then "
                            "return redis.call('del', KEYS[1]) "
                            "else return 0 end",
                            1,
                            f"ai-memory:{content_type}:{fingerprint}",
                            owner,
                        )
                    except Exception:
                        logger.warning("Não foi possível liberar lock Redis.")
                try:
                    await redis.aclose()
                except Exception:
                    logger.warning("Não foi possível fechar conexão Redis.")

        # A chamada externa nunca mantém uma transação aberta.
        await self.db.rollback()
        try:
            result = schema.model_validate(generator())
        except Exception:
            if acquired:
                await self._finish(fingerprint, content_type, owner, None)
            raise
        cache_id = None
        if acquired:
            cache_id = await self._finish(
                fingerprint,
                content_type,
                owner,
                result.model_dump(mode="json"),
            )
        return result, "ai", cache_id

    async def _finish(self, fingerprint, content_type, owner, payload):
        try:
            cache = await self.cache.get_for_update(fingerprint, content_type)
            if cache is None or cache.lease_owner != owner:
                await self.db.rollback()
                return None
            if payload is None:
                await self.cache.release_failed(cache, "generation_failed")
            else:
                await self.cache.publish_ready(cache, payload)
            cache_id = cache.id
            await self.db.commit()
            return cache_id
        except Exception:
            await self.db.rollback()
            logger.warning("Não foi possível atualizar memória de IA.")
            return None
