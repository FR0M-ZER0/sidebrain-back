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

    async def get_mentor_message(
        self, user_id: UUID, generation_id: UUID
    ) -> dict[str, Any]:
        base = await self.generations.get_context(user_id, generation_id)
        if base is None:
            raise ValueError("Contexto indisponível.")
        return base

    async def get_mentor_tool_data(
        self, user_id: UUID, base: dict[str, Any], name: str
    ) -> dict[str, Any]:
        if name == "consultar_historico":
            data = {
                "historico": await self.generations.list_previous_messages(
                    user_id, UUID(base["conversation_id"]), base["sequence"]
                )
            }
        else:
            fields = {
                "consultar_trilha": ("trilha", "descricao_trilha", "etapas"),
                "consultar_progresso": ("progresso",),
                "consultar_avaliacoes": (
                    "respostas_recentes",
                    "avaliacao_inicial",
                ),
            }
            if name not in fields:
                raise ValueError("Ferramenta de mentoria desconhecida.")
            track = await self.contexts.get(user_id, UUID(base["track_id"]))
            if track is None:
                raise ValueError("Trilha indisponível.")
            data = {key: track[key] for key in fields[name] if key in track}

        for key in ("historico", "respostas_recentes", "etapas"):
            while len(
                json.dumps(data, ensure_ascii=False)
            ) > self.max_context_chars and data.get(key):
                data[key].pop(0 if key == "historico" else -1)
        if len(json.dumps(data, ensure_ascii=False)) > self.max_context_chars:
            data.pop("descricao_trilha", None)
        if len(json.dumps(data, ensure_ascii=False)) > self.max_context_chars:
            raise ValueError("Resultado da ferramenta excede o limite.")
        return data
