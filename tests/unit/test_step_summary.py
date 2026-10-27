from uuid import uuid4

import pytest

from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.services.step_summary_generator_service import (
    StepSummaryGeneratorService,
)
from sidebrain_back.services.step_summary_service import StepSummaryService


class FixedTopicClassifier:
    def __init__(self, topics):
        self.topics = topics

    def classify_topics(self, texts):
        assert len(texts) == len(self.topics)
        return self.topics


def generate_summary(reasons, rates, topics):
    answers = list(zip(reasons, rates, strict=True))
    classifier = FixedTopicClassifier(topics)
    return StepSummaryGeneratorService(classifier).generate_step_summary(
        answers
    )


def test_generate_step_summary_matches_the_pipeline_output():
    reasons = [
        "A resposta aponta que Python é uma linguagem de alto nível, "
        "o que é uma vantagem, porém a pergunta pede a principal "
        "vantagem para iniciantes, geralmente destacada como sintaxe "
        "simples e legibilidade. A resposta não "
        "menciona esses aspectos, ficando incompleta.",
        "A resposta fornece exatamente a sintaxe correta para criar "
        "uma lista vazia "
        "em Python (lista = []), atendendo plenamente à pergunta.",
        'A resposta "function" está incorreta; a palavra-chave correta '
        "para definir "
        'uma função em Python é "def".',
    ]

    summary = generate_summary(
        reasons,
        [
            AnswerRateEnum.ALMOST_GOT_IT,
            AnswerRateEnum.PERFECT,
            AnswerRateEnum.WRONG,
        ],
        ["python", "arrays", "funcoes"],
    )

    assert summary == (
        "Nesta etapa, você acertou 1 de 3 perguntas.\n\n"
        "Para revisar:\n"
        "- Python\n"
        "- Funções\n\n"
        "Pontos fortes:\n"
        "- Arrays"
    )


def test_summary_groups_predicted_topics_and_uses_persisted_rates():
    reason = (
        "A resposta está correta: `console.log()` ajuda a depurar valores."
    )
    summary = generate_summary(
        [
            reason,
            reason.upper(),
            "A resposta está incorreta: `return` retorna valores.",
        ],
        [
            AnswerRateEnum.PERFECT,
            AnswerRateEnum.GOOD,
            AnswerRateEnum.WRONG,
        ],
        ["async", "async", "funcoes"],
    )

    assert summary.startswith("Nesta etapa, você acertou 2 de 3 perguntas.")
    review, strengths = summary.split("Pontos fortes:")
    assert "- Funções" in review
    assert "- Assincronismo" in strengths
    assert "respostas)" not in summary


def test_summary_renders_classifier_topic_labels():
    summary = generate_summary(
        ["Está correta: `console.log()` ajuda a depurar partes do código."],
        [AnswerRateEnum.PERFECT],
        ["dom"],
    )

    assert summary == (
        "Nesta etapa, você acertou 1 de 1 pergunta.\n\n"
        "Para revisar:\n"
        "- Nenhum tópico identificado nesta seção.\n\n"
        "Pontos fortes:\n"
        "- DOM"
    )


def test_summary_groups_different_labels_from_classifier():
    summary = generate_summary(
        [
            "A resposta está incompleta: faltou explicar que return "
            "encerra a função.",
            "A resposta está correta: o atributo defer adia a execução.",
            "A resposta está correta: a sintaxe const define uma variável.",
        ],
        [
            AnswerRateEnum.ALMOST_GOT_IT,
            AnswerRateEnum.GOOD,
            AnswerRateEnum.PERFECT,
        ],
        ["funcoes", "html", "variaveis"],
    )

    assert summary.startswith("Nesta etapa, você acertou 2 de 3 perguntas.")
    assert "- Funções" in summary
    assert "- HTML" in summary
    assert "- Variáveis" in summary


def test_summary_counts_repeated_topics_by_answer_rate():
    summary = generate_summary(
        ["Justificativa da resposta."] * 19,
        [AnswerRateEnum.PERFECT] * 5 + [AnswerRateEnum.WRONG] * 14,
        ["python"] * 19,
    )

    assert summary.startswith("Nesta etapa, você acertou 5 de 19 perguntas.")
    assert summary.count("- Python") == 2
    assert "respostas)" not in summary


def test_summary_counts_saved_rate_instead_of_reclassifying_verdict():
    summary = generate_summary(
        ["Console.log imprime valores no console."],
        [AnswerRateEnum.PERFECT],
        ["nodejs"],
    )

    assert summary.startswith("Nesta etapa, você acertou 1 de 1 pergunta.")
    assert "Console.log" not in summary
    assert "- Node.js" in summary


def test_summary_groups_different_reasons_in_the_same_class():
    summary = generate_summary(
        [
            "A resposta está incorreta. A pergunta pede tratar exceções.",
            "A resposta está incompleta. A pergunta pede capturar exceções.",
        ],
        [AnswerRateEnum.WRONG, AnswerRateEnum.ALMOST_GOT_IT],
        ["tratamento_erros", "tratamento_erros"],
    )

    assert "- Tratamento de erros" in summary
    assert summary.count("Tratamento de erros") == 1


def test_generate_step_summary_matches_empty_pipeline_output():
    assert (
        StepSummaryGeneratorService().generate_step_summary([])
        == "Nenhuma pergunta foi processada."
    )


@pytest.mark.anyio
async def test_refresh_summary_uses_only_non_empty_reasons_for_the_quiz_step():
    user_id = uuid4()
    quiz_id = uuid4()
    step_id = uuid4()

    class RepositorySpy:
        def __init__(self):
            self.updated = None

        async def get_step_id_by_quiz_id(
            self, requested_user_id, requested_quiz_id
        ):
            assert requested_user_id == user_id
            assert requested_quiz_id == quiz_id
            return step_id

        async def list_answers_by_step_id(
            self, requested_user_id, requested_step_id
        ):
            assert requested_user_id == user_id
            assert requested_step_id == step_id
            return [
                (" reason one ", AnswerRateEnum.GOOD),
                (None, AnswerRateEnum.WRONG),
                ("  ", AnswerRateEnum.WRONG),
                ("reason two", AnswerRateEnum.ALMOST_GOT_IT),
            ]

        async def update_summary(self, requested_step_id, summary):
            self.updated = (requested_step_id, summary)

    class GeneratorSpy:
        def __init__(self):
            self.answers = None

        def generate_step_summary(self, answers):
            self.answers = answers
            return "Resumo gerado."

    repository = RepositorySpy()
    generator = GeneratorSpy()
    await StepSummaryService(repository, generator).refresh_summary_for_quiz(
        user_id, quiz_id
    )

    assert repository.updated[0] == step_id
    assert repository.updated[1] == "Resumo gerado."
    assert generator.answers == [
        ("reason one", AnswerRateEnum.GOOD),
        ("reason two", AnswerRateEnum.ALMOST_GOT_IT),
    ]


@pytest.mark.anyio
async def test_refresh_summary_skips_quiz_without_accessible_step():
    class RepositorySpy:
        async def get_step_id_by_quiz_id(self, _user_id, _quiz_id):
            return None

        async def list_answers_by_step_id(self, _user_id, _step_id):
            raise AssertionError("reasons must not be queried")

        async def update_summary(self, _step_id, _summary):
            raise AssertionError("summary must not be persisted")

    await StepSummaryService(RepositorySpy()).refresh_summary_for_quiz(
        uuid4(), uuid4()
    )
