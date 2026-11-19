import asyncio
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.constants import Env
from sidebrain_back.core.database import get_db
from sidebrain_back.repositories.mentor_consent_repository import (
    MentorConsentRepository,
    get_mentor_consent_repository,
)
from sidebrain_back.schemas.mentor_consent_schema import MentorConsentResponse
from sidebrain_back.services.auth_errors import ConflictError

NOTICE_VERSION = "3"


class MentorConsentUnavailable(Exception):
    """The requested operation cannot be safely completed yet."""


class MentorConsentService:
    def __init__(
        self,
        repository: MentorConsentRepository,
        db: AsyncSession,
        *,
        wait_seconds: float = 1.0,
    ) -> None:
        self.repository = repository
        self.db = db
        self.wait_seconds = wait_seconds

    def _notice(self) -> tuple[str, str]:
        if Env.OPENAI_CHAT_API_KEY and Env.OPENAI_CHAT_API_KEY.strip():
            return f"{NOTICE_VERSION}-openai", "OpenAI"
        if Env.GROQ_API_KEY and Env.GROQ_API_KEY.strip():
            return f"{NOTICE_VERSION}-groq", "Groq"
        raise MentorConsentUnavailable("Provedor de IA não configurado.")

    async def get_mentor_consent(self, user_id: UUID) -> MentorConsentResponse:
        consent = await self.repository.get(user_id)
        block = await self.repository.get_privacy(user_id)
        notice_version, recipient = self._notice()
        authorized = bool(
            consent
            and consent.revoked_at is None
            and consent.notice_version == notice_version
            and (block is None or not block.blocked)
        )
        return MentorConsentResponse(
            notice_version=notice_version,
            purpose="Gerar orientações de mentoria para a trilha escolhida.",
            recipient=recipient,
            data_categories=[
                "mensagens",
                "dados da trilha escolhida",
                "conteúdo de lições e perguntas de quizzes solicitados",
                "progresso e avaliações vinculados",
            ],
            retention_notice=(
                "Excluir a conversa no SideBrain não apaga dados já enviados "
                "ao provedor. A retenção depende do contrato e da "
                "configuração aplicáveis ao serviço externo."
            ),
            authorized=authorized,
            granted_at=consent.granted_at if authorized else None,
        )

    async def accept_mentor_consent(
        self, user_id: UUID, notice_version: str
    ) -> MentorConsentResponse:
        current_version, _ = self._notice()
        if notice_version != current_version:
            raise ConflictError("A versão do aviso está desatualizada.")
        try:
            block = await self.repository.lock_privacy(user_id)
            if block.blocked:
                raise MentorConsentUnavailable(
                    "Há uma operação de privacidade pendente."
                )
            await self.repository.accept(user_id, notice_version)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return await self.get_mentor_consent(user_id)

    async def revoke_mentor_consent(self, user_id: UUID) -> None:
        deadline = asyncio.get_running_loop().time() + self.wait_seconds
        try:
            while True:
                block = await self.repository.lock_privacy(user_id)
                if block.blocked and block.reason != "revocation":
                    raise MentorConsentUnavailable(
                        "Há outra operação de privacidade pendente."
                    )
                block.blocked = True
                block.reason = "revocation"
                if not await self.repository.has_inflight(user_id):
                    await self.repository.revoke(user_id)
                    block.blocked = False
                    block.reason = None
                    await self.db.commit()
                    return

                # Commit before waiting so the worker can finish while new
                # reservations remain blocked.
                await self.db.commit()
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise MentorConsentUnavailable(
                        "Há um envio em andamento ou inconclusivo."
                    )
                await asyncio.sleep(min(0.1, remaining))
        except MentorConsentUnavailable:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise


def get_mentor_consent_service(
    repository: MentorConsentRepository = Depends(  # noqa: B008
        get_mentor_consent_repository
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> MentorConsentService:
    return MentorConsentService(repository, db)
