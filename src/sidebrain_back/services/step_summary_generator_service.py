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

        review_counts_by_topic: Counter[str] = Counter()
        strength_counts_by_topic: Counter[str] = Counter()
        topic_counts: Counter[str] = Counter()
        for (_reason, rate), topic in zip(answers, topics, strict=True):
            label = _TOPIC_LABELS.get(topic, topic.replace("_", " ").title())
            topic_counts[label] += 1
            counts_by_topic = (
                strength_counts_by_topic
                if rate in _CORRECT_RATES
                else review_counts_by_topic
            )
            counts_by_topic[label] += 1

        difficulty_counts: Counter[str] = Counter()
        strength_counts: Counter[str] = Counter()
        for topic in topic_counts:
            review_count = review_counts_by_topic[topic]
            strength_count = strength_counts_by_topic[topic]
            if strength_count > review_count:
                strength_counts[topic] = strength_count
            else:
                # Empates ficam em "Para revisar" por segurança.
                difficulty_counts[topic] = review_count

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
