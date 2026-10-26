import re
from collections import Counter

from sidebrain_back.services.step_summary_analysis_service import (
    StepSummaryAnalysisService,
)
from sidebrain_back.services.step_summary_topic_service import (
    StepSummaryTopicService,
)

_CODE_TOPIC_PATTERN = re.compile(
    r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*(?:\(\))?"
)


class StepSummaryGeneratorService:
    def __init__(self):
        self.analysis_service = StepSummaryAnalysisService()
        self.topic_service = StepSummaryTopicService()

    def generate_step_summary(self, texts: list[str]) -> str:
        if not texts:
            return "Nenhuma pergunta foi processada."

        analyses = self.analysis_service.analyze_reasons(texts)
        if not analyses:
            return "Nenhuma pergunta foi processada."

        total_questions = len(analyses)
        correct_answers = sum(
            analysis["verdict"] == "correct" for analysis in analyses
        )
        question_noun = "pergunta" if total_questions == 1 else "perguntas"
        opening = (
            f"Nesta etapa, você acertou {correct_answers} de "
            f"{total_questions} {question_noun}."
        )

        difficulty_counts = Counter()
        strength_counts = Counter()
        labels = {}
        for text, analysis in zip(texts, analyses, strict=True):
            topic = self.topic_service.extract_topic(text, analysis)
            if not topic:
                continue
            topic = " ".join(topic.split()).rstrip(".!?")
            if not topic:
                continue
            key = topic.casefold()
            label = (
                topic
                if _CODE_TOPIC_PATTERN.fullmatch(topic)
                else topic[0].upper() + topic[1:]
            )
            labels.setdefault(key, label)
            if analysis["verdict"] == "correct":
                strength_counts[key] += 1
            elif analysis["verdict"] in {"incorrect", "incomplete"}:
                difficulty_counts[key] += 1

        sections = [opening]
        for heading, counts in (
            ("Para revisar", difficulty_counts),
            ("Pontos fortes", strength_counts),
        ):
            lines = [f"{heading}:"]
            for key, repetitions in counts.most_common():
                detail = (
                    f" ({repetitions} respostas)" if repetitions > 1 else ""
                )
                lines.append(f"- {labels[key]}{detail}")
            if not counts:
                lines.append(
                    "- As justificativas não forneceram detalhes suficientes "
                    "para listar pontos nesta seção."
                )
            sections.append("\n".join(lines))
        return "\n\n".join(sections)
