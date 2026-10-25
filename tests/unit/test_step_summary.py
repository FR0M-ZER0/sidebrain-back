from uuid import uuid4

import pytest

from sidebrain_back.services.step_summary_generator_service import (
    StepSummaryGeneratorService,
)
from sidebrain_back.services.step_summary_service import StepSummaryService


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
        "Nesta etapa, você acertou 1 de 3 perguntas. Os pontos para "
        "revisar são as vantagens do Python para iniciantes e a "
        "definição de funções em Python. Você demonstrou bom domínio "
        "sobre a criação de listas vazias em Python."
    )


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
