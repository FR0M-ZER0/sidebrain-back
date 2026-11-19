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
        self,
        user_id: UUID,
        base: dict[str, Any],
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if name == "consultar_historico":
            data = {
                "historico": await self.generations.list_previous_messages(
                    user_id, UUID(base["conversation_id"]), base["sequence"]
                )
            }
        elif name in {"consultar_licao", "consultar_quiz"}:
            title = (arguments or {}).get("titulo")
            if not isinstance(title, str) or not (
                3 <= len(title.strip()) <= 255
            ):
                return {"erro": "Peça ao estudante o título da lição."}
            track_id = UUID(base["track_id"])
            lessons = await self.contexts.list_lessons_by_title(
                user_id, track_id, title.strip()
            )
            if not lessons:
                return {"erro": "Lição não encontrada; peça outro título."}
            if len(lessons) > 1:
                return {"erro": "Título ambíguo; peça um título mais preciso."}
            lesson = lessons[0]
            if name == "consultar_licao":
                data = {
                    "titulo": lesson["titulo"],
                    "conteudo": lesson["texto"][:10000],
                }
            else:
                questions = (
                    await self.contexts.list_quiz_questions_by_lesson_id(
                        user_id, track_id, lesson["id"]
                    )
                )
                data = {"titulo": lesson["titulo"], "perguntas": questions}
        else:
            fields = {
                "consultar_trilha": ("trilha", "descricao_trilha", "etapas"),
                "consultar_progresso": ("progresso",),
                "consultar_avaliacoes": (
                    "respostas_recentes",
                    "avaliacao_inicial",
                ),
                "analisar_desempenho": (
                    "progresso",
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
            if name == "analisar_desempenho":
                progress = track.get("progresso", {})
                total = progress.get("aulas", 0)
                completed = progress.get("concluidas", 0)
                data["percentual_conclusao"] = (
                    round(completed * 100 / total, 1) if total else None
                )
                data["limites"] = (
                    "Conclusão de aulas não mede domínio; resultados recentes "
                    "podem ser insuficientes para identificar dificuldades."
                )

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
