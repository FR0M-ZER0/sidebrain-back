import json

from sidebrain_back.core.constants import Env
from sidebrain_back.core.groq_client import get_groq_client
from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum


class QuizEvaluationService:
    def evaluate(self, question: str, answer: str) -> AnswerRateEnum:
        prompt = (
            "Avalie uma resposta aberta para a pergunta do quiz. "
            "Use perfect (completa), good (correta), "
            "almost_got_it (parcial) ou wrong (incorreta). "
            "Considere equivalências "
            "em outros termos e idiomas. Retorne JSON com a chave rate. "
            f"Pergunta: {question}\nResposta: {answer}"
        )
        response = get_groq_client().chat.completions.create(
            model=Env.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        content = (
            response.choices[0].message.content if response.choices else None
        )
        if not content:
            raise ValueError(
                "A IA não retornou uma avaliação para a resposta."
            )

        try:
            result = json.loads(content)
            return AnswerRateEnum(result["rate"])
        except (
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            raise ValueError(
                "A avaliação da IA não respeitou o formato esperado."
            ) from error
