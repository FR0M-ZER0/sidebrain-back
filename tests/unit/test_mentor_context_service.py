import json
from unittest.mock import AsyncMock

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
