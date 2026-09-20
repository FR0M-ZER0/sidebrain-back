from __future__ import annotations

import json

from sidebrain_back.core.constants import Env
from sidebrain_back.core.groq_client import get_groq_client


class KnowledgeAssessmentGenerator:
    def __init__(self, client: object | None = None) -> None:
        self.client = client or get_groq_client()

    def _build_prompt(self, subject: str, objective: str | None) -> str:
        objective_text = f" Objetivo: {objective}." if objective else ""
        return (
            "Responda somente em JSON. Crie uma avaliação de conhecimento "
            f"para o assunto '{subject}'.{objective_text} "
            "Retorne um objeto com os campos 'assessment_id', 'status', "
            "'level', e 'questions'. 'status' deve ser 'generated'. "
            "'level' deve ser null. 'questions' deve conter exatamente "
            "5 itens, "
            "cada um com 'id', 'statement' e 'alternatives' (4 alternativas). "
            "Cada alternativa deve ter 'id' e 'text'."
        )

    def generate(self, subject: str, objective: str | None = None) -> dict:
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

        return payload
