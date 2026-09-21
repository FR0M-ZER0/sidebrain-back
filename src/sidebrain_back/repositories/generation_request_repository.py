from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.enums.generation_status_enum import GenerationStatusEnum
from sidebrain_back.models.generation_request_model import GenerationRequest


class GenerationRequestRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, request_id: UUID) -> GenerationRequest | None:
        return await self.db.scalar(
            select(GenerationRequest).where(
                GenerationRequest.request_id == request_id
            )
        )

    async def create_pending(
        self,
        *,
        request_id: UUID,
        user_id: UUID,
        context_fingerprint: str,
        goal: str,
        topic: str,
        knowledge_level: str | None,
        assessment_answers: list[dict] | None,
    ) -> GenerationRequest:
        request = GenerationRequest(
            request_id=request_id,
            user_id=user_id,
            context_fingerprint=context_fingerprint,
            goal=goal,
            topic=topic,
            knowledge_level=knowledge_level,
            assessment_answers=assessment_answers,
            status=GenerationStatusEnum.PENDING,
        )
        self.db.add(request)
        await self.db.flush()
        return request

    async def mark_succeeded(self, request_id: UUID, track_id: UUID) -> None:
        request = await self.get(request_id)
        if request is None:
            return
        request.status = GenerationStatusEnum.SUCCEEDED
        request.track_id = track_id
        request.error_code = None
        request.updated_at = datetime.now(UTC).replace(tzinfo=None)

    async def mark_failed(self, request_id: UUID, error_code: str) -> None:
        request = await self.get(request_id)
        if request is None:
            return
        request.status = GenerationStatusEnum.FAILED
        request.track_id = None
        request.error_code = error_code
        request.updated_at = datetime.now(UTC).replace(tzinfo=None)
