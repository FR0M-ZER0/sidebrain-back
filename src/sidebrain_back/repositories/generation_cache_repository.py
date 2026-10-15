from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.enums.generation_cache_enum import (
    GenerationCacheContentTypeEnum,
    GenerationCacheStatusEnum,
)
from sidebrain_back.models.generation_cache_model import GenerationCache


class GenerationCacheRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_ready(
        self, fingerprint: str, content_type: GenerationCacheContentTypeEnum
    ) -> GenerationCache | None:
        return await self.db.scalar(
            select(GenerationCache).where(
                GenerationCache.fingerprint == fingerprint,
                GenerationCache.content_type == content_type,
                GenerationCache.status == GenerationCacheStatusEnum.READY,
            )
        )

    async def get_for_update(
        self, fingerprint: str, content_type: GenerationCacheContentTypeEnum
    ) -> GenerationCache | None:
        return await self.db.scalar(
            select(GenerationCache)
            .where(
                GenerationCache.fingerprint == fingerprint,
                GenerationCache.content_type == content_type,
            )
            .with_for_update()
        )

    async def reserve(
        self,
        *,
        fingerprint: str,
        content_type: GenerationCacheContentTypeEnum,
        fingerprint_version: str,
        prompt_version: str,
        provider: str,
        model: str,
        canonical_context: dict,
        lease_owner: str | None = None,
        lease_seconds: int = 120,
    ) -> tuple[GenerationCache, bool]:
        now = datetime.now(UTC).replace(tzinfo=None)
        cache = await self.get_for_update(fingerprint, content_type)
        if cache is None:
            cache = GenerationCache(
                id=uuid4(),
                fingerprint=fingerprint,
                content_type=content_type,
                fingerprint_version=fingerprint_version,
                prompt_version=prompt_version,
                provider=provider,
                model=model,
                canonical_context=canonical_context,
                status=GenerationCacheStatusEnum.PENDING,
            )
            self.db.add(cache)
            try:
                await self.db.flush()
            except IntegrityError:
                await self.db.rollback()
                cache = await self.get_for_update(fingerprint, content_type)
                if cache is None:
                    raise
        if cache.status is GenerationCacheStatusEnum.READY:
            return cache, False
        if (
            cache.lease_expires_at is not None
            and cache.lease_expires_at > now
            and cache.lease_owner != lease_owner
        ):
            return cache, False
        cache.status = GenerationCacheStatusEnum.PENDING
        cache.lease_owner = lease_owner
        cache.lease_expires_at = now + timedelta(seconds=lease_seconds)
        cache.failure_code = None
        await self.db.flush()
        return cache, True

    async def wait_for_ready(
        self,
        fingerprint: str,
        content_type: GenerationCacheContentTypeEnum,
        *,
        timeout_seconds: int,
        poll_interval_seconds: float = 0.1,
    ) -> GenerationCache | None:
        import asyncio

        deadline = datetime.now(UTC).timestamp() + timeout_seconds
        while datetime.now(UTC).timestamp() < deadline:
            cache = await self.get_ready(fingerprint, content_type)
            if cache is not None:
                return cache
            await asyncio.sleep(poll_interval_seconds)
        return None

    async def publish_ready(
        self, cache: GenerationCache, payload: dict
    ) -> GenerationCache:
        cache.payload = payload
        cache.status = GenerationCacheStatusEnum.READY
        cache.lease_owner = None
        cache.lease_expires_at = None
        cache.failure_code = None
        await self.db.flush()
        return cache

    async def release_failed(
        self, cache: GenerationCache, failure_code: str
    ) -> None:
        cache.status = GenerationCacheStatusEnum.FAILED
        cache.payload = None
        cache.failure_code = failure_code
        cache.lease_owner = None
        cache.lease_expires_at = None
        await self.db.flush()
