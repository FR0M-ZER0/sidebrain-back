from __future__ import annotations

import json
from uuid import uuid4

from sidebrain_back.core.constants import Env
from sidebrain_back.core.groq_client import get_groq_client


class KnowledgeAssessmentGenerator:
    def __init__(self, client: object | None = None) -> None:
        self.client = client or get_groq_client()

    def _make_question(self, number: int, subject: str, objective: str | None) -> dict:
        objective_suffix = f" para {objective}" if objective else ""
        return {
            "id": f"q{number}",
            "statement": (
                f"Qual opção melhor descreve o conhecimento necessário sobre "
                f"{subject}{objective_suffix}?"
            ),
            "alternatives": [
                {
                    "id": "a",
                    "text": f"Domínio básico de {subject} e aplicação prática no contexto solicitado.",
                },
                {
                    "id": "b",
                    "text": f"Conhecimento superficial apenas teórico sobre {subject}.",
                },
                {
                    "id": "c",
                    "text": f"Falta de entendimento sobre {subject}{objective_suffix}.",
                },
                {
                    "id": "d",
                    "text": f"Aplicação avançada de {subject} com autonomia para criar soluções.",
                },
            ],
        }

    def _fallback_payload(self, subject: str, objective: str | None) -> dict:
        return {
            "assessment_id": str(uuid4()),
            "status": "generated",
            "level": None,
            "questions": [
                self._make_question(index, subject, objective)
                for index in range(1, 6)
            ],
        }

    def _build_prompt(self, subject: str, objective: str | None) -> str:
        objective_text = f" Objetivo: {objective}." if objective else ""
        return (
            "Responda somente em JSON. Crie uma avaliação de conhecimento "
            f"para o assunto '{subject}'.{objective_text} "
            "Retorne um objeto com os campos 'assessment_id', 'status', "
            "'level', e 'questions'. 'status' deve ser 'generated'. "
            "'level' deve ser null. 'questions' deve conter exatamente 5 itens, "
            "cada um com 'id', 'statement' e 'alternatives' (4 alternativas). "
            "Cada alternativa deve ter 'id' e 'text'."
        )

    def generate(self, subject: str, objective: str | None = None) -> dict:
        if not subject or not subject.strip():
            raise ValueError("Assunto obrigatório para gerar a avaliação.")

        try:
            response = self.client.chat.completions.create(
                model=Env.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você gera avaliações de conhecimento em JSON válido. "
                            "Responda somente com o objeto solicitado."
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
        except Exception:
            return self._fallback_payload(subject, objective)

        content = getattr(response.choices[0].message, "content", None)
        if not isinstance(content, str) or not content.strip():
            return self._fallback_payload(subject, objective)

        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return self._fallback_payload(subject, objective)

        if not isinstance(payload, dict):
            raise ValueError("Resposta do provedor inválida.")

        payload.setdefault("assessment_id", str(uuid4()))
        payload.setdefault("status", "generated")
        payload.setdefault("level", None)
        if "questions" not in payload:
            payload["questions"] = self._fallback_payload(subject, objective)["questions"]

        return payload
