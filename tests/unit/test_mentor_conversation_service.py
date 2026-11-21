import pytest

from sidebrain_back.services.mentor_context_service import MentorContextService


@pytest.mark.anyio
async def test_followup_uses_history_only_from_selected_conversation():
    expected_conversation = "00000000-0000-0000-0000-000000000002"

    class Generations:
        async def get_context(self, _user_id, _generation_id):
            return {
                "track_id": "00000000-0000-0000-0000-000000000001",
                "conversation_id": expected_conversation,
                "sequence": 4,
                "mensagem": "Tenho dez minutos.",
            }

        async def list_previous_messages(self, _user_id, conversation_id, seq):
            assert str(conversation_id) == expected_conversation
            assert seq == 4
            return [
                {"role": "student", "content": "Estou estudando Python."},
                {"role": "mentor", "content": "Revise funções."},
            ]

    class Contexts:
        async def get(self, _user_id, _track_id):
            return {"trilha": "Python"}

    service = MentorContextService(Generations(), Contexts())
    base = await service.get_mentor_message("usuario", "geracao")
    context = await service.get_mentor_tool_data(
        "usuario", base, "consultar_historico"
    )
    assert base["mensagem"] == "Tenho dez minutos."
    assert [item["content"] for item in context["historico"]] == [
        "Estou estudando Python.",
        "Revise funções.",
    ]
