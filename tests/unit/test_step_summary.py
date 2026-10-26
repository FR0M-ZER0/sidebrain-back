from uuid import uuid4

import pytest

from sidebrain_back.services.step_summary_generator_service import (
    StepSummaryGeneratorService,
)
from sidebrain_back.services.step_summary_service import StepSummaryService
from sidebrain_back.services.step_summary_topic_service import (
    StepSummaryTopicService,
)


def test_generate_step_summary_matches_the_pipeline_output():
    generator = StepSummaryGeneratorService()
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

    summary = generator.generate_step_summary(reasons)

    assert summary == (
        "Nesta etapa, você acertou 1 de 3 perguntas.\n\n"
        "Para revisar:\n"
        "- As vantagens do Python para iniciantes\n"
        "- A definição de funções em Python\n\n"
        "Pontos fortes:\n"
        "- A criação de listas vazias em Python"
    )


@pytest.mark.parametrize(
    "reason,verdict,keywords",
    [
        (
            "A resposta está incompleta: faltou explicitar que return "
            "devolve um valor e encerra a função.",
            "incomplete",
            ["explicitar que", "return", "função"],
        ),
        (
            "A resposta está correta: o atributo defer adia a execução "
            "do script até o HTML ser analisado.",
            "correct",
            ["atributo", "defer", "adia"],
        ),
        (
            "A resposta está correta: `console.log()` ajuda a depurar "
            "valores no JavaScript.",
            "correct",
            ["console", "log", "ajuda a depurar"],
        ),
        (
            "A resposta está incorreta: o operador === não converte "
            "tipos antes da comparação.",
            "incorrect",
            ["operador", "converte", "comparação"],
        ),
    ],
)
def test_topic_fallback_returns_the_central_term(reason, verdict, keywords):
    topic = StepSummaryTopicService().extract_topic(
        reason, {"verdict": verdict, "keywords": keywords}
    )

    expected = {
        "incomplete": "return",
        "correct": "defer" if "defer" in reason else "console.log()",
        "incorrect": "comparação",
    }[verdict]
    assert topic == expected


def test_review_fallback_prefers_the_missing_content_over_praise():
    topic = StepSummaryTopicService().extract_topic(
        "A resposta menciona funções e parâmetros. "
        "Faltou explicar que return encerra a função.",
        {
            "verdict": "incomplete",
            "keywords": ["funções", "parâmetros", "return"],
        },
    )

    assert topic == "return"


def test_inline_code_topic_is_extracted_even_inside_a_long_target():
    topic = StepSummaryTopicService().extract_topic(
        "A pergunta pede explicar o comportamento de `return` em funções.",
        {"verdict": "correct", "keywords": ["return", "funções"]},
    )

    assert topic == "return"


@pytest.mark.parametrize(
    "reason,keywords",
    [
        ("Adequado quando isto.", ["adequado quando", "isto"]),
        ("Função.", ["resultado"]),
        ("A função " + "executa " * 60 + "o cálculo.", ["resultado"]),
    ],
)
def test_topic_fallback_omits_noise_or_overlong_fragments(reason, keywords):
    assert (
        StepSummaryTopicService().extract_topic(
            reason, {"verdict": "correct", "keywords": keywords}
        )
        is None
    )


def test_summary_groups_repeated_evidence_and_preserves_score():
    reason = (
        "A resposta está correta: `console.log()` ajuda a depurar valores."
    )
    summary = StepSummaryGeneratorService().generate_step_summary(
        [
            reason,
            reason.upper(),
            "A resposta está incorreta: `return` retorna valores.",
        ]
    )

    assert summary.startswith("Nesta etapa, você acertou 2 de 3 perguntas.")
    assert summary.count("console.log") == 1
    assert "(2 respostas)" in summary
    review, strengths = summary.split("Pontos fortes:")
    assert "- return" in review
    assert "- console.log() (2 respostas)" in strengths


def test_summary_uses_only_the_central_code_topic():
    summary = StepSummaryGeneratorService().generate_step_summary(
        ["Está correta: `console.log()` ajuda a depurar partes do código."]
    )

    assert summary == (
        "Nesta etapa, você acertou 1 de 1 pergunta.\n\n"
        "Para revisar:\n"
        "- As justificativas não forneceram detalhes suficientes para "
        "listar pontos nesta seção.\n\n"
        "Pontos fortes:\n"
        "- console.log()"
    )


def test_summary_prefers_language_keywords_to_surrounding_explanations():
    summary = StepSummaryGeneratorService().generate_step_summary(
        [
            "A resposta está incompleta: faltou explicar que return "
            "encerra a função.",
            "A resposta está correta: o atributo defer adia a execução.",
            "A resposta está correta: a sintaxe const define uma variável.",
        ]
    )

    assert summary.startswith("Nesta etapa, você acertou 2 de 3 perguntas.")
    assert "- return" in summary
    assert "- defer" in summary
    assert "- const" in summary
    assert "explicar" not in summary
    assert "define uma variável" not in summary


def test_summary_preserves_five_of_nineteen_without_inventing_topics():
    summary = StepSummaryGeneratorService().generate_step_summary(
        ["Resposta correta."] * 5 + ["Resposta incorreta."] * 14
    )

    assert summary.startswith("Nesta etapa, você acertou 5 de 19 perguntas.")
    assert "Para revisar:" in summary
    assert "Pontos fortes:" in summary
    assert "não forneceram detalhes suficientes" in summary
    assert "bom domínio" not in summary


def test_unknown_verdict_is_not_presented_as_an_error_or_strength():
    summary = StepSummaryGeneratorService().generate_step_summary(
        ["Console.log imprime valores no console."]
    )

    assert summary.startswith("Nesta etapa, você acertou 0 de 1 pergunta.")
    assert "Console.log" not in summary


def test_summary_groups_topics_from_different_reasons():
    summary = StepSummaryGeneratorService().generate_step_summary(
        [
            "A resposta está incorreta. A pergunta pede tratar exceções.",
            "A resposta está incompleta. A pergunta pede capturar exceções.",
        ]
    )

    assert "- O tratamento de exceções (2 respostas)" in summary
    assert summary.count("tratamento de exceções") == 1
    assert "Python" not in summary


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

        async def list_reasons_by_step_id(
            self, requested_user_id, requested_step_id
        ):
            assert requested_user_id == user_id
            assert requested_step_id == step_id
            return [" reason one ", None, "  ", "reason two"]

        async def update_summary(self, requested_step_id, summary):
            self.updated = (requested_step_id, summary)

    repository = RepositorySpy()
    await StepSummaryService(repository).refresh_summary_for_quiz(
        user_id, quiz_id
    )

    assert repository.updated[0] == step_id
    assert repository.updated[1].startswith("Nesta etapa, você acertou")


@pytest.mark.anyio
async def test_refresh_summary_skips_quiz_without_accessible_step():
    class RepositorySpy:
        async def get_step_id_by_quiz_id(self, _user_id, _quiz_id):
            return None

        async def list_reasons_by_step_id(self, _user_id, _step_id):
            raise AssertionError("reasons must not be queried")

        async def update_summary(self, _step_id, _summary):
            raise AssertionError("summary must not be persisted")

    await StepSummaryService(RepositorySpy()).refresh_summary_for_quiz(
        uuid4(), uuid4()
    )
