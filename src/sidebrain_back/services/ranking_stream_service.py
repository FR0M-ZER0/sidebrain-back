import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import UUID

from fastapi import Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.user_model import User
from sidebrain_back.services.ranking_service import (
    RankingService,
    get_ranking_service,
)

POLL_INTERVAL_SECONDS = 5
MAX_POLLS = 12


class RankingStreamService:
    def __init__(self, ranking: RankingService, db: AsyncSession):
        self.ranking = ranking
        self.db = db

    async def list_rankings(self, page: int, page_size: int) -> BaseModel:
        try:
            return await self.ranking.list_rankings(page, page_size)
        finally:
            # Não manter uma conexão ou transação aberta entre consultas.
            await self.db.rollback()

    async def get_my_ranking(self, user_id: UUID) -> BaseModel:
        try:
            return await self.ranking.get_my_ranking(User(usr_id=user_id))
        finally:
            await self.db.rollback()

    async def stream(
        self,
        request: Request,
        event: str,
        initial: BaseModel,
        read: Callable[[], Awaitable[BaseModel]],
    ) -> AsyncIterator[str]:
        current = initial.model_dump_json(by_alias=True)
        yield f"event: {event}\ndata: {current}\n\n"
        for poll in range(1, MAX_POLLS + 1):
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            if await request.is_disconnected():
                return
            updated = (await read()).model_dump_json(by_alias=True)
            if updated != current:
                current = updated
                yield f"event: {event}\ndata: {current}\n\n"
            elif poll % 3 == 0:
                yield ": keep-alive\n\n"


def get_ranking_stream_service(
    ranking: RankingService = Depends(get_ranking_service),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> RankingStreamService:
    return RankingStreamService(ranking, db)
