from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.mentor_conversation_model import MentorConversation
from sidebrain_back.models.mentor_generation_model import (
    MentorDispatch,
    MentorGeneration,
    MentorSendReservation,
)
from sidebrain_back.models.mentor_message_model import MentorMessage
from sidebrain_back.models.track_model import Track
from sidebrain_back.repositories.mentor_consent_repository import (
    MentorConsentRepository,
)


class MentorGenerationConflict(Exception):
    """The request conflicts with an existing generation."""


class MentorGenerationConsentRequired(MentorGenerationConflict):
    """The generation cannot be sent without current authorization."""


class MentorGenerationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(
        self, user_id: UUID, conversation_id: UUID, generation_id: UUID
    ) -> MentorGeneration | None:
        return await self.db.scalar(
            select(MentorGeneration)
            .join(
                MentorConversation,
                MentorConversation.id == MentorGeneration.conversation_id,
            )
            .join(Track, Track.trk_id == MentorConversation.track_id)
            .where(
                MentorGeneration.id == generation_id,
                MentorGeneration.conversation_id == conversation_id,
                MentorConversation.user_id == user_id,
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
        )

    async def get_response_id(self, generation_id: UUID) -> UUID | None:
        return await self.db.scalar(
            select(MentorMessage.id).where(
                MentorMessage.generation_id == generation_id
            )
        )

    async def get_by_key(
        self, conversation_id: UUID, idempotency_key: UUID
    ) -> MentorGeneration | None:
        return await self.db.scalar(
            select(MentorGeneration).where(
                MentorGeneration.conversation_id == conversation_id,
                MentorGeneration.idempotency_key == idempotency_key,
            )
        )

    async def validate_submission_replay(
        self, generation: MentorGeneration, content: str
    ) -> None:
        message = await self.db.get(
            MentorMessage, generation.student_message_id
        )
        if (
            message is None
            or message.content != content
            or generation.retry_of_generation_id is not None
        ):
            raise MentorGenerationConflict(
                "Chave de idempotência associada a outro conteúdo."
            )

    async def get_context(
        self, user_id: UUID, generation_id: UUID
    ) -> dict[str, Any] | None:
        result = (
            await self.db.execute(
                select(
                    Track.trk_title,
                    Track.trk_description,
                    Track.trk_id,
                    MentorConversation.id.label("conversation_id"),
                    MentorMessage.content,
                    MentorMessage.sequence,
                )
                .join(
                    MentorConversation,
                    MentorConversation.track_id == Track.trk_id,
                )
                .join(
                    MentorGeneration,
                    MentorGeneration.conversation_id == MentorConversation.id,
                )
                .join(
                    MentorMessage,
                    MentorMessage.id == MentorGeneration.student_message_id,
                )
                .where(
                    MentorGeneration.id == generation_id,
                    MentorConversation.user_id == user_id,
                    Track.trk_user_id == user_id,
                    Track.trk_is_deleted.is_(False),
                )
            )
        ).one_or_none()
        if result is None:
            return None
        return {
            "trilha": result.trk_title,
            "descricao_trilha": result.trk_description,
            "mensagem": result.content,
            "track_id": str(result.trk_id),
            "conversation_id": str(result.conversation_id),
            "sequence": result.sequence,
        }

    async def list_previous_messages(
        self, user_id: UUID, conversation_id: UUID, sequence: int
    ) -> list[dict[str, str]]:
        rows = (
            await self.db.execute(
                select(MentorMessage.role, MentorMessage.content)
                .join(
                    MentorConversation,
                    MentorConversation.id == MentorMessage.conversation_id,
                )
                .join(Track, Track.trk_id == MentorConversation.track_id)
                .where(
                    MentorConversation.id == conversation_id,
                    MentorConversation.user_id == user_id,
                    Track.trk_user_id == user_id,
                    Track.trk_is_deleted.is_(False),
                    MentorMessage.sequence < sequence,
                )
                .order_by(MentorMessage.sequence.desc())
                .limit(40)
            )
        ).all()
        return [
            {"role": row.role, "content": row.content}
            for row in reversed(rows)
        ]

    async def create(
        self, conversation_id: UUID, idempotency_key: UUID, content: str
    ) -> MentorGeneration:
        conversation = await self.db.scalar(
            select(MentorConversation)
            .where(MentorConversation.id == conversation_id)
            .with_for_update()
        )
        if conversation is None:
            raise ValueError("Conversa não encontrada.")
        existing = await self.get_by_key(conversation_id, idempotency_key)
        if existing is not None:
            await self.validate_submission_replay(existing, content)
            return existing

        active = await self.db.scalar(
            select(MentorGeneration.id).where(
                MentorGeneration.conversation_id == conversation_id,
                MentorGeneration.status.in_(("queued", "processing")),
            )
        )
        if active is not None:
            raise MentorGenerationConflict("A conversa já tem geração ativa.")
        last_sequence = await self.db.scalar(
            select(func.max(MentorMessage.sequence)).where(
                MentorMessage.conversation_id == conversation_id
            )
        )
        message = MentorMessage(
            conversation_id=conversation_id,
            sequence=(last_sequence or 0) + 1,
            role="student",
            content=content,
        )
        self.db.add(message)
        await self.db.flush()
        generation = MentorGeneration(
            conversation_id=conversation_id,
            student_message_id=message.id,
            idempotency_key=idempotency_key,
            status="queued",
        )
        self.db.add(generation)
        await self.db.flush()
        self.db.add(MentorDispatch(generation_id=generation.id))
        await self.db.flush()
        return generation

    async def reserve(
        self, user_id: UUID, generation_id: UUID, notice_version: str
    ) -> MentorSendReservation:
        privacy = MentorConsentRepository(self.db)
        block = await privacy.lock_privacy(user_id)
        if block.blocked or await privacy.has_inflight(user_id):
            raise MentorGenerationConflict("Envio indisponível.")
        consent = await privacy.get(user_id)
        if (
            consent is None
            or consent.revoked_at is not None
            or consent.notice_version != notice_version
        ):
            raise MentorGenerationConsentRequired("Autorização necessária.")

        generation = await self.db.scalar(
            select(MentorGeneration)
            .join(
                MentorConversation,
                MentorConversation.id == MentorGeneration.conversation_id,
            )
            .join(Track, Track.trk_id == MentorConversation.track_id)
            .where(
                MentorGeneration.id == generation_id,
                MentorConversation.user_id == user_id,
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
            .with_for_update(of=MentorGeneration)
        )
        if generation is None or generation.status != "queued":
            raise MentorGenerationConflict("Geração indisponível.")
        attempt_id = uuid4()
        generation.status = "processing"
        generation.attempt_id = attempt_id
        generation.attempt_count += 1
        generation.attempt_deadline = datetime.now(UTC).replace(
            tzinfo=None
        ) + timedelta(seconds=60)
        reservation = MentorSendReservation(
            user_id=user_id,
            generation_id=generation_id,
            attempt_id=attempt_id,
            status="in_flight",
        )
        self.db.add(reservation)
        await self.db.flush()
        return reservation

    async def fail_unauthorized(
        self, user_id: UUID, generation_id: UUID, notice_version: str
    ) -> None:
        privacy = MentorConsentRepository(self.db)
        block = await privacy.lock_privacy(user_id)
        if block.blocked:
            return
        consent = await privacy.get(user_id)
        if (
            consent is not None
            and consent.revoked_at is None
            and consent.notice_version == notice_version
        ):
            return
        generation = await self.db.scalar(
            select(MentorGeneration)
            .join(
                MentorConversation,
                MentorConversation.id == MentorGeneration.conversation_id,
            )
            .where(
                MentorGeneration.id == generation_id,
                MentorConversation.user_id == user_id,
                MentorGeneration.status == "queued",
            )
            .with_for_update(of=MentorGeneration)
        )
        if generation is not None:
            generation.status = "failed"
            generation.error_code = "consent_required"
            await self.db.flush()

    async def retry(
        self, conversation_id: UUID, generation_id: UUID, idempotency_key: UUID
    ) -> MentorGeneration:
        conversation = await self.db.scalar(
            select(MentorConversation)
            .where(MentorConversation.id == conversation_id)
            .with_for_update()
        )
        if conversation is None:
            raise ValueError("Conversa não encontrada.")
        original = await self.db.scalar(
            select(MentorGeneration).where(
                MentorGeneration.id == generation_id,
                MentorGeneration.conversation_id == conversation_id,
            )
        )
        if original is None or original.status != "failed":
            raise MentorGenerationConflict("Geração não pode ser repetida.")
        existing = await self.get_by_key(conversation_id, idempotency_key)
        if existing is not None:
            if existing.retry_of_generation_id != original.id:
                raise MentorGenerationConflict("Chave já está em uso.")
            return existing
        active = await self.db.scalar(
            select(MentorGeneration.id).where(
                MentorGeneration.conversation_id == conversation_id,
                MentorGeneration.status.in_(("queued", "processing")),
            )
        )
        if active is not None:
            raise MentorGenerationConflict("A conversa já tem geração ativa.")
        generation = MentorGeneration(
            conversation_id=conversation_id,
            student_message_id=original.student_message_id,
            retry_of_generation_id=original.id,
            idempotency_key=idempotency_key,
            status="queued",
        )
        self.db.add(generation)
        await self.db.flush()
        self.db.add(MentorDispatch(generation_id=generation.id))
        await self.db.flush()
        return generation

    async def complete(
        self,
        user_id: UUID,
        generation_id: UUID,
        attempt_id: UUID,
        content: str,
        notice_version: str,
    ) -> MentorMessage | None:
        privacy = MentorConsentRepository(self.db)
        block = await privacy.lock_privacy(user_id)
        reservation = await self.db.scalar(
            select(MentorSendReservation)
            .where(
                MentorSendReservation.user_id == user_id,
                MentorSendReservation.generation_id == generation_id,
                MentorSendReservation.attempt_id == attempt_id,
                MentorSendReservation.status == "in_flight",
            )
            .with_for_update()
        )
        if reservation is None:
            return None
        generation = await self.db.scalar(
            select(MentorGeneration)
            .where(MentorGeneration.id == generation_id)
            .with_for_update()
        )
        reservation.status = "finished"
        reservation.finished_at = datetime.now(UTC).replace(tzinfo=None)
        consent = await privacy.get(user_id)
        track_id = await self.db.scalar(
            select(Track.trk_id)
            .join(
                MentorConversation,
                MentorConversation.track_id == Track.trk_id,
            )
            .join(
                MentorGeneration,
                MentorGeneration.conversation_id == MentorConversation.id,
            )
            .where(
                MentorGeneration.id == generation_id,
                MentorConversation.user_id == user_id,
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
        )
        if (
            generation is None
            or generation.status != "processing"
            or generation.attempt_id != attempt_id
            or track_id is None
            or block.blocked
            or consent is None
            or consent.revoked_at is not None
            or consent.notice_version != notice_version
        ):
            if (
                generation is not None
                and generation.status == "processing"
                and generation.attempt_id == attempt_id
            ):
                generation.status = "failed"
                generation.error_code = "generation_cancelled"
            await self.db.flush()
            return None
        sequence = await self.db.scalar(
            select(func.max(MentorMessage.sequence)).where(
                MentorMessage.conversation_id == generation.conversation_id
            )
        )
        message = MentorMessage(
            conversation_id=generation.conversation_id,
            generation_id=generation.id,
            sequence=(sequence or 0) + 1,
            role="mentor",
            content=content,
        )
        generation.status = "completed"
        generation.error_code = None
        self.db.add(message)
        await self.db.flush()
        return message

    async def fail_attempt(
        self,
        user_id: UUID,
        generation_id: UUID,
        attempt_id: UUID,
        *,
        transient: bool,
        notice_version: str,
    ) -> None:
        privacy = MentorConsentRepository(self.db)
        block = await privacy.lock_privacy(user_id)
        reservation = await self.db.scalar(
            select(MentorSendReservation)
            .where(
                MentorSendReservation.user_id == user_id,
                MentorSendReservation.generation_id == generation_id,
                MentorSendReservation.attempt_id == attempt_id,
                MentorSendReservation.status == "in_flight",
            )
            .with_for_update()
        )
        if reservation is None:
            return
        generation = await self.db.scalar(
            select(MentorGeneration)
            .where(MentorGeneration.id == generation_id)
            .with_for_update()
        )
        reservation.status = "finished"
        reservation.finished_at = datetime.now(UTC).replace(tzinfo=None)
        if (
            generation is None
            or generation.status != "processing"
            or generation.attempt_id != attempt_id
        ):
            await self.db.flush()
            return
        consent = await privacy.get(user_id)
        if (
            transient
            and generation.attempt_count < 3
            and not block.blocked
            and consent is not None
            and consent.revoked_at is None
            and consent.notice_version == notice_version
        ):
            generation.status = "queued"
            generation.error_code = None
        else:
            generation.status = "failed"
            generation.error_code = "generation_failed"
        await self.db.flush()

    async def reconcile_expired(
        self,
        user_id: UUID,
        generation_id: UUID,
        attempt_id: UUID,
        notice_version: str,
    ) -> None:
        privacy = MentorConsentRepository(self.db)
        block = await privacy.lock_privacy(user_id)
        now = datetime.now(UTC).replace(tzinfo=None)
        generation = await self.db.scalar(
            select(MentorGeneration)
            .join(
                MentorConversation,
                MentorConversation.id == MentorGeneration.conversation_id,
            )
            .where(
                MentorGeneration.id == generation_id,
                MentorConversation.user_id == user_id,
                MentorGeneration.status == "processing",
                MentorGeneration.attempt_id == attempt_id,
                MentorGeneration.attempt_deadline < now,
            )
            .with_for_update(of=MentorGeneration)
        )
        if generation is None:
            return
        has_inflight = await privacy.has_inflight(user_id)
        consent = await privacy.get(user_id)
        if (
            not has_inflight
            and not block.blocked
            and generation.attempt_count < 3
            and consent is not None
            and consent.revoked_at is None
            and consent.notice_version == notice_version
        ):
            generation.status = "queued"
            generation.error_code = None
        else:
            generation.status = "failed"
            generation.error_code = "generation_interrupted"
        generation.attempt_id = None
        generation.attempt_deadline = None
        await self.db.flush()


def get_mentor_generation_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> MentorGenerationRepository:
    return MentorGenerationRepository(db)
