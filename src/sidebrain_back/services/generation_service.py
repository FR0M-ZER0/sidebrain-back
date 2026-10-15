import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.constants import Env
from sidebrain_back.core.groq_client import get_groq_client
from sidebrain_back.repositories.generation_cache_repository import (
    GenerationCacheRepository,
)
from sidebrain_back.repositories.generation_repository import (
    GenerationRepository,
)
from sidebrain_back.repositories.generation_request_repository import (
    GenerationRequestRepository,
)
from sidebrain_back.schemas.generation_schema import (
    GeneratedTrack,
    GenerationInput,
    GenerationSuccess,
)
from sidebrain_back.services.ai_memory_service import AIMemoryService
from sidebrain_back.services.generation_errors import (
    GenerationPersistenceError,
    GenerationValidationError,
)


class GenerationService:
    def __init__(
        self,
        repository: GenerationRepository,
        db: AsyncSession,
        request_repository: GenerationRequestRepository | None = None,
        cache_repository: GenerationCacheRepository | None = None,
    ):
        self.repository = repository
        self.db = db
        self.request_repository = request_repository
        self.cache_repository = cache_repository

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
            "Gere uma trilha completa em JSON. Escolha um único emoji "
            "que represente o tema e o objetivo de aprendizagem e retorne-o "
            "no campo icon. Retorne um único "
            "objeto JSON, sem texto fora dele, com exatamente as "
            "chaves icon, title, description e steps. O campo icon deve "
            "conter apenas um emoji, sem texto ou espaço adicional. "
            "Não retorne uma "
            "lista. Inclua todas as etapas na ordem da progressão, "
            "com position contíguas a partir de 1. Gere conteúdo "
            "detalhado somente para a etapa de posição 1; etapas "
            "posteriores devem conter apenas posição, nível e "
            "título, com lessons=[] e mission=null. Cada etapa tem "
            "position, level, title, lessons e mission. level deve "
            "ser um de beginner, intermediate, advanced, pro, sem "
            "repetir. Cada lesson da etapa 1 tem position, title, "
            "text e quiz.question, com positions contíguas a "
            "partir de 1. mission pode ser null ou ter title, "
            "difficulty (easy, medium, hard, very_hard), "
            "xp_reward, criteria (number_of_lessons_completed, "
            "get_all_answer_right_in_a_lesson, complete_a_step, "
            "complete_a_track, number_of_steps_completed, "
            "get_all_answers_right) e criteria_value. Não crie IDs, "
            "timestamps, objectives, content ou outros campos. As lições devem"
            "ter no mínimo 420 caracteres."
            "Contexto: "
            f"{json.dumps(context, ensure_ascii=True)}"
        )

    def generate_with_ai(self, payload: GenerationInput) -> GeneratedTrack:
        response = get_groq_client().chat.completions.create(
            model=Env.GROQ_MODEL,
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
            if self.request_repository:
                await self.request_repository.mark_succeeded(
                    payload.request_id, existing.trk_id
                )
                await self.db.commit()
            return GenerationSuccess(
                request_id=payload.request_id, track_id=existing.trk_id
            )
        cache = None
        cache_owner = str(payload.request_id)
        cache_owner_acquired = False
        if self.cache_repository and Env.AI_MEMORY_ENABLED:
            try:
                context = AIMemoryService.track_context(
                    payload.goal,
                    payload.topic,
                    knowledge_level=(
                        payload.knowledge_level.value
                        if payload.knowledge_level
                        else None
                    ),
                    assessment_answers=[
                        answer.model_dump(mode="json")
                        for answer in payload.assessment_answers or []
                    ],
                )
                fingerprint, envelope = AIMemoryService.fingerprint(
                    content_type="track",
                    canonical_context=context,
                    provider="groq",
                    model=Env.GROQ_MODEL,
                )
                cache = await self.cache_repository.get_ready(
                    fingerprint, "track"
                )
                if cache is not None and cache.payload is not None:
                    generated = GeneratedTrack.model_validate(cache.payload)
                    source = "cache"
                else:
                    (
                        cache,
                        cache_owner_acquired,
                    ) = await self.cache_repository.reserve(
                        fingerprint=fingerprint,
                        content_type="track",
                        fingerprint_version=envelope["fingerprint_version"],
                        prompt_version=envelope["prompt_version"],
                        provider=envelope["provider"],
                        model=envelope["model"],
                        canonical_context=envelope["canonical_context"],
                        lease_owner=cache_owner,
                        lease_seconds=Env.AI_MEMORY_LEASE_SECONDS,
                    )
                    await self.db.commit()
                    if not cache_owner_acquired:
                        cache = await self.cache_repository.wait_for_ready(
                            fingerprint,
                            "track",
                            timeout_seconds=Env.AI_MEMORY_LEASE_SECONDS,
                        )
                        if cache is not None and cache.payload is not None:
                            generated = GeneratedTrack.model_validate(
                                cache.payload
                            )
                            source = "cache"
                        else:
                            (
                                cache,
                                cache_owner_acquired,
                            ) = await self.cache_repository.reserve(
                                fingerprint=fingerprint,
                                content_type="track",
                                fingerprint_version=envelope[
                                    "fingerprint_version"
                                ],
                                prompt_version=envelope["prompt_version"],
                                provider=envelope["provider"],
                                model=envelope["model"],
                                canonical_context=envelope[
                                    "canonical_context"
                                ],
                                lease_owner=cache_owner,
                                lease_seconds=Env.AI_MEMORY_LEASE_SECONDS,
                            )
                            await self.db.commit()
                    if cache_owner_acquired:
                        generated = self.generate_with_ai(payload)
                        source = "ai"
            except (ValueError, TypeError, IntegrityError):
                await self.db.rollback()
                cache = None
                cache_owner_acquired = False
                generated = self.generate_with_ai(payload)
                source = "ai"
        else:
            generated = self.generate_with_ai(payload)
            source = "ai"
        try:
            if self.db.in_transaction():
                await self.db.rollback()
            async with self.db.begin():
                track = await self.repository.create(
                    payload.user_id, payload.request_id, generated
                )
                if (
                    cache is not None
                    and cache_owner_acquired
                    and source == "ai"
                ):
                    await self.cache_repository.publish_ready(
                        cache, generated.model_dump(mode="json")
                    )
                if self.request_repository:
                    await self.request_repository.mark_succeeded(
                        payload.request_id, track.trk_id
                    )
                    await self.request_repository.set_source(
                        payload.request_id,
                        source=source,
                        cache_id=cache.id if cache is not None else None,
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
