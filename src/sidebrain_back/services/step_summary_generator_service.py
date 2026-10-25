from collections import Counter

from sidebrain_back.services.step_summary_analysis_service import (
    StepSummaryAnalysisService,
    format_human_list,
)
from sidebrain_back.services.step_summary_topic_service import (
    StepSummaryTopicService,
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
        strengths = []
        for text, analysis in zip(texts, analyses, strict=True):
            topic = self.topic_service.extract_topic(text, analysis)
            if analysis["verdict"] == "correct":
                if topic:
                    strengths.append(topic)
            elif analysis["verdict"] in {"incorrect", "incomplete"} and topic:
                difficulty_counts[topic] += 1

        parts = [opening]
        if difficulty_counts:
            difficulty_topics = [
                topic for topic, _ in difficulty_counts.most_common()
            ]
            if len(difficulty_topics) == 1:
                topic = difficulty_topics[0]
                repetitions = difficulty_counts[topic]
                repetition_detail = (
                    f" ({repetitions} perguntas)" if repetitions > 1 else ""
                )
                parts.append(
                    f"O ponto para revisar é {topic}{repetition_detail}."
                )
            else:
                parts.append(
                    "Os pontos para revisar são "
                    f"{format_human_list(difficulty_topics)}."
                )
        else:
            parts.append(
                "Não foram identificados pontos específicos para revisar."
            )

        strengths = list(dict.fromkeys(strengths))
        if strengths:
            if len(strengths) == 1:
                parts.append(
                    f"Você demonstrou bom domínio sobre {strengths[0]}."
                )
            else:
                parts.append(
                    "Você demonstrou bom domínio em temas como "
                    f"{format_human_list(strengths)}."
                )
        else:
            parts.append(
                "Ainda não foram identificados pontos fortes nesta etapa."
            )

        return " ".join(parts)
