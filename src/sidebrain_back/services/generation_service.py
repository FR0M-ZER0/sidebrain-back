import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.groq_client import get_groq_client
from sidebrain_back.repositories.generation_repository import (
    GenerationRepository,
)
from sidebrain_back.schemas.generation_schema import (
    GeneratedTrack,
    GenerationInput,
    GenerationSuccess,
)
from sidebrain_back.services.generation_errors import (
    GenerationPersistenceError,
    GenerationValidationError,
)


class GenerationService:
    def __init__(self, repository: GenerationRepository, db: AsyncSession):
        self.repository = repository
        self.db = db

    @staticmethod
    def build_prompt(payload: GenerationInput) -> str:
        context = {
            "goal": payload.goal,
            "topic": payload.topic,
            "knowledge_level": payload.knowledge_level.value
            if payload.knowledge_level
            else None,
            "assessment_answers": [
                answer.model_dump()
                for answer in payload.assessment_answers or []
            ],
        }
        return (
            "Gere uma trilha completa em JSON. Inclua todas as etapas "
            "na ordem "
            "da progressão. Gere conteúdo detalhado somente para a etapa de "
            "posição 1; etapas posteriores devem conter apenas posição, nível "
            "e título. Não inclua texto fora do JSON. Contexto: "
            f"{json.dumps(context, ensure_ascii=True)}"
        )

    def generate_with_ai(self, payload: GenerationInput) -> GeneratedTrack:
        response = get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": self.build_prompt(payload)}],
            response_format={"type": "json_object"},
        )
        content = (
            response.choices[0].message.content if response.choices else None
        )
        if not content:
            raise GenerationValidationError()
        try:
            return GeneratedTrack.model_validate_json(content)
        except (TypeError, ValueError):
            raise GenerationValidationError() from None

    async def generate(self, payload: GenerationInput):
        existing = await self.repository.get_by_request_id(payload.request_id)
        if existing:
            return GenerationSuccess(
                request_id=payload.request_id, track_id=existing.trk_id
            )
        generated = self.generate_with_ai(payload)
        try:
            if self.db.in_transaction():
                await self.db.rollback()
            async with self.db.begin():
                track = await self.repository.create(
                    payload.user_id, payload.request_id, generated
                )
        except IntegrityError:
            await self.db.rollback()
            existing = await self.repository.get_by_request_id(
                payload.request_id
            )
            if existing:
                return GenerationSuccess(
                    request_id=payload.request_id, track_id=existing.trk_id
                )
            raise GenerationPersistenceError() from None
        except Exception:
            await self.db.rollback()
            raise GenerationPersistenceError() from None
        return GenerationSuccess(
            request_id=payload.request_id, track_id=track.trk_id
        )
