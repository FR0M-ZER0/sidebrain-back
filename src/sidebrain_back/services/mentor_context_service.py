import json
from typing import Any
from uuid import UUID

from sidebrain_back.repositories.mentor_context_repository import (
    MentorContextRepository,
)
from sidebrain_back.repositories.mentor_generation_repository import (
    MentorGenerationRepository,
)


class MentorContextService:
    def __init__(
        self,
        generations: MentorGenerationRepository,
        contexts: MentorContextRepository,
        *,
        max_context_chars: int = 16000,
    ) -> None:
        self.generations = generations
        self.contexts = contexts
        self.max_context_chars = max_context_chars

    async def build(
        self, user_id: UUID, generation_id: UUID
    ) -> dict[str, Any]:
        base = await self.generations.get_context(user_id, generation_id)
        if base is None:
            raise ValueError("Contexto indisponível.")
        track = await self.contexts.get(user_id, UUID(base["track_id"]))
        if track is None:
            raise ValueError("Trilha indisponível.")
        history = await self.generations.list_previous_messages(
            user_id, UUID(base["conversation_id"]), base["sequence"]
        )
        result = {
            **track,
            "historico": history,
            "mensagem": base["mensagem"],
        }
        for field in ("respostas_recentes", "etapas", "historico"):
            while len(
                json.dumps(result, ensure_ascii=False)
            ) > self.max_context_chars and result.get(field):
                result[field].pop(0 if field == "historico" else -1)
        remaining_size = len(json.dumps(result, ensure_ascii=False))
        if remaining_size > self.max_context_chars:
            result["descricao_trilha"] = ""
        return result
