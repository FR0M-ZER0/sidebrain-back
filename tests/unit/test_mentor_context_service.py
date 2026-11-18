import json

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
    result = await service.build("user", "generation")
    assert result["mensagem"] == "Mensagem atual"
    assert result["trilha"] == "Python"
    assert "track_id" not in result
    assert len(json.dumps(result, ensure_ascii=False)) <= 3000
