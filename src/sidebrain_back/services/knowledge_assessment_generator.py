from __future__ import annotations

import json

from sidebrain_back.core.constants import Env
from sidebrain_back.core.groq_client import get_groq_client
from sidebrain_back.schemas.knowledge_assessment_schema import (
    GeneratedAssessmentPayload,
)


class KnowledgeAssessmentGenerator:
    def __init__(self, client: object | None = None) -> None:
        self.client = client or get_groq_client()

    def _build_prompt(self, subject: str, objective: str | None) -> str:
        objective_text = f" Objetivo: {objective}." if objective else ""
        return (
            "Responda somente em JSON. Crie uma avaliação de conhecimento "
            f"para o assunto '{subject}'.{objective_text} "
            "Retorne um objeto que contenha somente 'questions'. "
            "'questions' deve conter exatamente 5 itens distintos; cada "
            "item deve possuir 'id', 'statement', 'alternatives' com "
            "exatamente 4 alternativas distintas e "
            "'correct_alternative_id'. Cada alternativa deve possuir "
            "somente 'id' e 'text'. O 'correct_alternative_id' deve ser o "
            "id de exatamente uma alternativa da própria pergunta."
        )

    def generate(
        self,
        subject: str,
        objective: str | None = None,
    ) -> GeneratedAssessmentPayload:
        if not subject or not subject.strip():
            raise ValueError("Assunto obrigatório para gerar a avaliação.")

        response = self.client.chat.completions.create(
            model=Env.GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você gera avaliações de conhecimento em JSON "
                        "válido. Responda somente com o objeto solicitado."
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_prompt(subject, objective),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            timeout=30,
        )

        content = getattr(response.choices[0].message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Resposta vazia do provedor.")

        payload = json.loads(content)
        if not isinstance(payload, dict):
            raise ValueError("Resposta do provedor inválida.")
        return GeneratedAssessmentPayload.model_validate(payload)
