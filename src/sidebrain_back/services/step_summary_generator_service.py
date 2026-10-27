from collections import Counter

from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.services.step_summary_classifier_service import (
    StepSummaryClassifierService,
)

_TOPIC_LABELS = {
    "arrays": "Arrays",
    "async": "Assincronismo",
    "classes": "Classes",
    "condicionais": "Condicionais",
    "dom": "DOM",
    "funcoes": "Funções",
    "html": "HTML",
    "nodejs": "Node.js",
    "objetos": "Objetos",
    "python": "Python",
    "strings": "Strings",
    "testes": "Testes",
    "tratamento_erros": "Tratamento de erros",
    "variaveis": "Variáveis",
}
_CORRECT_RATES = {AnswerRateEnum.GOOD, AnswerRateEnum.PERFECT}


class StepSummaryGeneratorService:
    def __init__(
        self, classifier: StepSummaryClassifierService | None = None
    ) -> None:
        self.classifier = classifier or StepSummaryClassifierService()

    def generate_step_summary(
        self, answers: list[tuple[str, AnswerRateEnum]]
    ) -> str:
        if not answers:
            return "Nenhuma pergunta foi processada."

        topics = self.classifier.classify_topics(
            [reason for reason, _rate in answers]
        )
        total_questions = len(answers)
        correct_answers = sum(
            rate in _CORRECT_RATES for _reason, rate in answers
        )
        question_noun = "pergunta" if total_questions == 1 else "perguntas"
        opening = (
            f"Nesta etapa, você acertou {correct_answers} de "
            f"{total_questions} {question_noun}."
        )

        difficulty_counts: Counter[str] = Counter()
        strength_counts: Counter[str] = Counter()
        for (_reason, rate), topic in zip(answers, topics, strict=True):
            label = _TOPIC_LABELS.get(topic, topic.replace("_", " ").title())
            counts = (
                strength_counts
                if rate in _CORRECT_RATES
                else difficulty_counts
            )
            counts[label] += 1

        sections = [opening]
        for heading, counts in (
            ("Para revisar", difficulty_counts),
            ("Pontos fortes", strength_counts),
        ):
            lines = [f"{heading}:"]
            for topic, _count in counts.most_common():
                lines.append(f"- {topic}")
            if not counts:
                lines.append("- Nenhum tópico identificado nesta seção.")
            sections.append("\n".join(lines))
        return "\n\n".join(sections)
