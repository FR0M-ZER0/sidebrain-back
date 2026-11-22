from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.repositories.mentor_consent_repository import (
    MentorConsentRepository,
    get_mentor_consent_repository,
)
from sidebrain_back.repositories.mentor_context_repository import (
    MentorContextRepository,
    get_mentor_context_repository,
)
from sidebrain_back.repositories.mentor_conversation_repository import (
    MentorConversationRepository,
    get_mentor_conversation_repository,
)
from sidebrain_back.repositories.mentor_generation_repository import (
    MentorGenerationConflict,
    MentorGenerationRepository,
    get_mentor_generation_repository,
)
from sidebrain_back.schemas.mentor_schema import (
    MentorConversationResponse,
    MentorGenerationAccepted,
    MentorGenerationEvent,
    MentorGenerationResponse,
    MentorMessageCreate,
    MentorMessageResponse,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.services.mentor_consent_service import (
    MentorConsentService,
    MentorConsentUnavailable,
    get_mentor_consent_service,
)
from sidebrain_back.services.mentor_privacy_service import (
    MentorPrivacyService,
    get_mentor_privacy_service,
)


class MentorNotFound(Exception):
    pass


class MentorConsentRequired(Exception):
    pass


class MentorService:
    def __init__(
        self,
        conversation_repository: MentorConversationRepository,
        generation_repository: MentorGenerationRepository,
        consent_repository: MentorConsentRepository,
        consent_service: MentorConsentService,
        db: AsyncSession,
        privacy_service: MentorPrivacyService | None = None,
        context_repository: MentorContextRepository | None = None,
    ) -> None:
        self.conversations = conversation_repository
        self.generations = generation_repository
        self.consent = consent_repository
        self.consent_service = consent_service
        self.db = db
        self.privacy_service = privacy_service
        self.contexts = context_repository

    async def create_mentor_conversation(
        self, user_id: UUID, track_id: UUID
    ) -> MentorConversationResponse:
        try:
            block = await self.consent.lock_privacy(user_id)
            if block.blocked:
                raise MentorConsentUnavailable(
                    "Operação de privacidade ativa."
                )
            conversation = await self.conversations.create(user_id, track_id)
            if conversation is None:
                raise MentorNotFound("Trilha não encontrada.")
            response = MentorConversationResponse.model_validate(conversation)
            await self.db.commit()
            return response
        except Exception:
            await self.db.rollback()
            raise

    async def create_mentor_message(
        self,
        user_id: UUID,
        conversation_id: UUID,
        idempotency_key: UUID,
        payload: MentorMessageCreate,
    ) -> MentorGenerationAccepted:
        try:
            block = await self.consent.lock_privacy(user_id)
            conversation = await self.conversations.get(
                user_id, conversation_id
            )
            if conversation is None:
                raise MentorNotFound("Conversa não encontrada.")
            context = (
                payload.context.model_dump(mode="json", exclude_none=True)
                if payload.context is not None
                else None
            )
            existing = await self.generations.get_by_key(
                conversation_id, idempotency_key
            )
            if existing is not None:
                await self.generations.validate_submission_replay(
                    existing, payload.content, context
                )
                response = MentorGenerationAccepted(
                    generation_id=existing.id,
                    message_id=existing.student_message_id,
                    status=existing.status,
                )
                await self.db.commit()
                return response
            if block.blocked or await self.consent.has_inflight(user_id):
                raise MentorConsentUnavailable("Envio indisponível.")
            notice = await self.consent_service.get_mentor_consent(user_id)
            if not notice.authorized:
                raise MentorConsentRequired("Autorização necessária.")
            if context is not None:
                contexts = self.contexts or MentorContextRepository(self.db)
                screen = await contexts.get_screen_context(
                    user_id,
                    conversation.track_id,
                    payload.context.lesson_id,
                    getattr(payload.context, "quiz_id", None),
                    getattr(payload.context, "answer_id", None),
                )
                if screen is None:
                    raise MentorNotFound("Contexto indisponível.")
            generation = await self.generations.create(
                conversation_id, idempotency_key, payload.content, context
            )
            response = MentorGenerationAccepted(
                generation_id=generation.id,
                message_id=generation.student_message_id,
                status=generation.status,
            )
            await self.db.commit()
            return response
        except Exception:
            await self.db.rollback()
            raise

    async def get_mentor_message(
        self, user_id: UUID, conversation_id: UUID, message_id: UUID
    ) -> MentorMessageResponse:
        message = await self.conversations.get_message(
            user_id, conversation_id, message_id
        )
        if message is None:
            raise MentorNotFound("Mensagem não encontrada.")
        return MentorMessageResponse.model_validate(message)

    async def get_mentor_generation(
        self, user_id: UUID, conversation_id: UUID, generation_id: UUID
    ) -> MentorGenerationResponse:
        generation = await self.generations.get(
            user_id, conversation_id, generation_id
        )
        if generation is None:
            raise MentorNotFound("Geração não encontrada.")
        response_id = await self.generations.get_response_id(generation_id)
        return MentorGenerationResponse(
            id=generation.id,
            message_id=generation.student_message_id,
            status=generation.status,
            response_message_id=response_id,
            error_code=generation.error_code,
        )

    async def get_mentor_generation_event(
        self, user_id: UUID, conversation_id: UUID, generation_id: UUID
    ) -> MentorGenerationEvent:
        try:
            generation = await self.get_mentor_generation(
                user_id, conversation_id, generation_id
            )
            message = None
            if generation.status == "completed":
                if generation.response_message_id is None:
                    raise RuntimeError("Resposta de mentoria indisponível.")
                message = await self.get_mentor_message(
                    user_id, conversation_id, generation.response_message_id
                )
            return MentorGenerationEvent(
                generation=generation, message=message
            )
        finally:
            # Do not hold a database transaction while the client waits.
            await self.db.rollback()

    async def retry_mentor_generation(
        self,
        user_id: UUID,
        conversation_id: UUID,
        generation_id: UUID,
        idempotency_key: UUID,
    ) -> MentorGenerationAccepted:
        try:
            block = await self.consent.lock_privacy(user_id)
            original = await self.generations.get(
                user_id, conversation_id, generation_id
            )
            if original is None:
                raise MentorNotFound("Geração não encontrada.")
            existing = await self.generations.get_by_key(
                conversation_id, idempotency_key
            )
            if existing is not None:
                if existing.retry_of_generation_id != original.id:
                    raise MentorGenerationConflict("Chave já está em uso.")
                response = MentorGenerationAccepted(
                    generation_id=existing.id,
                    message_id=existing.student_message_id,
                    status=existing.status,
                )
                await self.db.commit()
                return response
            if block.blocked or await self.consent.has_inflight(user_id):
                raise MentorConsentUnavailable("Envio indisponível.")
            notice = await self.consent_service.get_mentor_consent(user_id)
            if not notice.authorized:
                raise MentorConsentRequired("Autorização necessária.")
            generation = await self.generations.retry(
                conversation_id, generation_id, idempotency_key
            )
            response = MentorGenerationAccepted(
                generation_id=generation.id,
                message_id=generation.student_message_id,
                status=generation.status,
            )
            await self.db.commit()
            return response
        except Exception:
            await self.db.rollback()
            raise

    async def get_mentor_conversation(
        self, user_id: UUID, conversation_id: UUID
    ) -> MentorConversationResponse:
        conversation = await self.conversations.get(user_id, conversation_id)
        if conversation is None:
            raise MentorNotFound("Conversa não encontrada.")
        return MentorConversationResponse.model_validate(conversation)

    async def list_mentor_conversations(
        self, user_id: UUID, page: int, page_size: int, track_id: UUID | None
    ) -> PaginatedResponse[MentorConversationResponse]:
        rows, total = await self.conversations.list(
            user_id, (page - 1) * page_size, page_size, track_id
        )
        return PaginatedResponse.build(
            [MentorConversationResponse.model_validate(item) for item in rows],
            page,
            page_size,
            total,
        )

    async def list_mentor_messages(
        self, user_id: UUID, conversation_id: UUID, page: int, page_size: int
    ) -> PaginatedResponse[MentorMessageResponse]:
        result = await self.conversations.list_messages(
            user_id, conversation_id, (page - 1) * page_size, page_size
        )
        if result is None:
            raise MentorNotFound("Conversa não encontrada.")
        rows, total = result
        return PaginatedResponse.build(
            [MentorMessageResponse.model_validate(item) for item in rows],
            page,
            page_size,
            total,
        )

    async def delete_mentor_conversations(
        self, user_id: UUID, conversation_id: UUID | None = None
    ) -> None:
        if self.privacy_service is None:
            raise RuntimeError("Serviço de privacidade não configurado.")
        try:
            if (
                conversation_id is not None
                and await self.conversations.get(user_id, conversation_id)
                is None
            ):
                raise MentorNotFound("Conversa não encontrada.")
            block = await self.privacy_service.lock_for_deletion(user_id)
            await self.conversations.delete(user_id, conversation_id)
            block.blocked = False
            block.reason = None
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise


def get_mentor_service(
    conversations: MentorConversationRepository = Depends(  # noqa: B008
        get_mentor_conversation_repository
    ),
    generations: MentorGenerationRepository = Depends(  # noqa: B008
        get_mentor_generation_repository
    ),
    consent: MentorConsentRepository = Depends(  # noqa: B008
        get_mentor_consent_repository
    ),
    consent_service: MentorConsentService = Depends(  # noqa: B008
        get_mentor_consent_service
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    privacy_service: MentorPrivacyService = Depends(  # noqa: B008
        get_mentor_privacy_service
    ),
    contexts: MentorContextRepository = Depends(  # noqa: B008
        get_mentor_context_repository
    ),
) -> MentorService:
    return MentorService(
        conversations,
        generations,
        consent,
        consent_service,
        db,
        privacy_service,
        contexts,
    )
