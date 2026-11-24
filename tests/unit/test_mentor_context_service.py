import json
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from sidebrain_back.services.mentor_context_service import MentorContextService


@pytest.mark.anyio
async def test_context_budget_preserves_current_message():
    class GenerationRepository:
        async def get_context(self, _user_id, _generation_id):
            return {
                "track_id": "00000000-0000-0000-0000-000000000001",
                "conversation_id": "00000000-0000-0000-0000-000000000002",
                "sequence": 3,
                "mensagem": "Mensagem atual",
            }

        async def list_previous_messages(self, *_args):
            return [{"role": "student", "content": "x" * 1000}] * 6

    class ContextRepository:
        async def get(self, _user_id, _track_id):
            return {
                "trilha": "Python",
                "etapas": [{"titulo": "y" * 500}] * 20,
                "respostas_recentes": [{"justificativa": "z" * 600}] * 20,
            }

    service = MentorContextService(
        GenerationRepository(), ContextRepository(), max_context_chars=3000
    )
    base = await service.get_mentor_message("user", "generation")
    result = await service.get_mentor_tool_data(
        "user", base, "consultar_trilha"
    )
    assert base["mensagem"] == "Mensagem atual"
    assert result["trilha"] == "Python"
    assert "track_id" not in result
    assert len(json.dumps(result, ensure_ascii=False)) <= 3000


@pytest.mark.anyio
async def test_history_budget_removes_oldest_complete_messages():
    generations = AsyncMock()
    generations.list_previous_messages.return_value = [
        {"role": "student", "content": "antiga " + "x" * 100},
        {"role": "mentor", "content": "recente " + "y" * 100},
    ]
    service = MentorContextService(
        generations, AsyncMock(), max_context_chars=180
    )
    base = {
        "conversation_id": str(UUID(int=2)),
        "sequence": 3,
        "mensagem": "Mensagem atual",
    }

    result = await service.get_mentor_tool_data(
        "usuario", base, "consultar_historico"
    )

    assert result["historico"] == [
        {"role": "mentor", "content": "recente " + "y" * 100}
    ]
    assert len(json.dumps(result, ensure_ascii=False)) <= 180
    assert base["mensagem"] == "Mensagem atual"
    generations.list_previous_messages.assert_awaited_once_with(
        "usuario", UUID(int=2), 3
    )


@pytest.mark.anyio
async def test_screen_context_budget_preserves_question_and_evaluation():
    contexts = AsyncMock()
    contexts.get_screen_context.return_value = {
        "tipo": "quiz",
        "licao": {"titulo": "Listas", "conteudo": "x" * 10000},
        "questao": "Pergunta atual?",
        "avaliacao": {
            "resposta": "resposta",
            "classificacao": "almost_got_it",
            "justificativa": "Faltou detalhe.",
        },
    }
    service = MentorContextService(
        AsyncMock(), contexts, max_context_chars=500
    )
    base = {
        "track_id": str(UUID(int=1)),
        "context": {
            "type": "quiz",
            "lesson_id": str(UUID(int=2)),
            "quiz_id": str(UUID(int=3)),
            "answer_id": str(UUID(int=4)),
        },
    }
    result = await service.get_mentor_screen_context("usuario", base)
    assert result["questao"] == "Pergunta atual?"
    assert result["avaliacao"]["resposta"] == "resposta"
    assert result["licao"]["conteudo_truncado"] is True
    assert len(json.dumps(result, ensure_ascii=False)) <= 500
    contexts.get_screen_context.assert_awaited_once_with(
        "usuario", UUID(int=1), UUID(int=2), UUID(int=3), UUID(int=4)
    )


@pytest.mark.anyio
async def test_tools_filter_data_and_reject_unknown_names():
    generations = AsyncMock()
    contexts = AsyncMock()
    contexts.get.return_value = {
        "trilha": "Python",
        "progresso": {"aulas": 2},
        "respostas_recentes": [{"justificativa": "privado"}],
    }
    service = MentorContextService(generations, contexts)
    base = {"track_id": "00000000-0000-0000-0000-000000000001"}
    result = await service.get_mentor_tool_data(
        "usuario", base, "consultar_progresso"
    )
    assert result == {"progresso": {"aulas": 2}}
    with pytest.raises(ValueError):
        await service.get_mentor_tool_data("usuario", base, "desconhecida")


@pytest.mark.anyio
async def test_lesson_and_quiz_are_scoped_and_ambiguous_titles_fail():
    generations = AsyncMock()
    contexts = AsyncMock()
    contexts.list_lessons_by_title.return_value = [
        {"id": "lesson", "titulo": "Funções", "texto": "Conteúdo"}
    ]
    contexts.list_quiz_questions_by_lesson_id.return_value = ["Pergunta?"]
    service = MentorContextService(generations, contexts)
    base = {"track_id": "00000000-0000-0000-0000-000000000001"}
    result = await service.get_mentor_tool_data(
        "usuario", base, "consultar_quiz", {"titulo": "Funções"}
    )
    assert result == {"titulo": "Funções", "perguntas": ["Pergunta?"]}
    contexts.list_quiz_questions_by_lesson_id.assert_awaited_once_with(
        "usuario", UUID(base["track_id"]), "lesson"
    )
    contexts.list_lessons_by_title.return_value *= 2
    result = await service.get_mentor_tool_data(
        "usuario", base, "consultar_licao", {"titulo": "Funções"}
    )
    assert "ambíguo" in result["erro"]


@pytest.mark.anyio
async def test_performance_metrics_do_not_treat_completion_as_mastery():
    contexts = AsyncMock()
    contexts.get.return_value = {
        "progresso": {"aulas": 4, "concluidas": 2},
        "respostas_recentes": [],
    }
    service = MentorContextService(AsyncMock(), contexts)
    result = await service.get_mentor_tool_data(
        "usuario", {"track_id": str(UUID(int=1))}, "analisar_desempenho"
    )
    assert result["percentual_conclusao"] == 50
    assert "não mede domínio" in result["limites"]
