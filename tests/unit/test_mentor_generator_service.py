import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from sidebrain_back.services.mentor_generator_service import (
    MentorGeneratorService,
)


def response(content=None, calls=None):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, tool_calls=calls)
            )
        ]
    )


def tool(name, arguments="{}"):
    return SimpleNamespace(
        id="call-1",
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


@pytest.mark.anyio
async def test_generator_sends_only_message_without_tool_calls():
    create = Mock(return_value=response('{"content":"Revise."}'))
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    lookup = AsyncMock()
    result = await MentorGeneratorService(
        client, "test"
    ).generate_mentor_response("Como estudar?", lookup)
    assert result == "Revise."
    lookup.assert_not_awaited()
    assert create.call_args.kwargs["messages"][1]["content"] == "Como estudar?"
    assert create.call_args.kwargs["tool_choice"] == "auto"
    assert "reasoning_effort" not in create.call_args.kwargs


@pytest.mark.anyio
async def test_luna_disables_reasoning_for_chat_tools():
    create = Mock(return_value=response('{"content":"Olá."}'))
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    service = MentorGeneratorService(client, "gpt-6-luna")
    await service.generate_mentor_response("Olá", AsyncMock())
    assert create.call_args.kwargs["reasoning_effort"] == "none"


@pytest.mark.anyio
async def test_generator_returns_only_requested_tool_data():
    requests = []

    def create(**kwargs):
        requests.append(copy.deepcopy(kwargs))
        if len(requests) == 1:
            return response(calls=[tool("consultar_progresso")])
        return response('{"content":"Continue estudando."}')

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    lookup = AsyncMock(return_value={"progresso": {"aulas": 5}})
    await MentorGeneratorService(client, "test").generate_mentor_response(
        "Como estou?", lookup
    )
    lookup.assert_awaited_once_with("consultar_progresso", {})
    assert len(requests[0]["messages"]) == 2
    assert json.loads(requests[1]["messages"][-1]["content"]) == {
        "progresso": {"aulas": 5}
    }


@pytest.mark.anyio
async def test_generator_forwards_lesson_title_and_quiz_policy():
    create = Mock(
        side_effect=[
            response(calls=[tool("consultar_quiz", '{"titulo":"Funções"}')]),
            response('{"content":"Pense em um exemplo."}'),
        ]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    lookup = AsyncMock(return_value={"perguntas": ["Pergunta?"]})
    await MentorGeneratorService(client, "test").generate_mentor_response(
        "Ajude com o quiz de Funções", lookup
    )
    lookup.assert_awaited_once_with("consultar_quiz", {"titulo": "Funções"})
    system = create.call_args_list[0].kwargs["messages"][0]["content"]
    assert "nunca forneça a resposta" in system
    assert "peça ao estudante o título" in system


@pytest.mark.anyio
@pytest.mark.parametrize(
    "call",
    [
        tool("outra"),
        tool("consultar_trilha", '{"user_id":"outro"}'),
        tool("consultar_trilha", "inválido"),
        tool("consultar_licao", "{}"),
        tool("consultar_quiz", '{"titulo":"Funções","user_id":"outro"}'),
        tool("consultar_quiz", '{"titulo":"  "}'),
    ],
)
async def test_generator_rejects_unknown_tools_and_arguments(call):
    create = Mock(return_value=response(calls=[call]))
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    lookup = AsyncMock()
    with pytest.raises(ValueError):
        await MentorGeneratorService(client, "test").generate_mentor_response(
            "Olá", lookup
        )
    lookup.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("content", [None, "", "{}", '{"content": "  "}'])
async def test_generator_rejects_invalid_output(content):
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=Mock(return_value=response(content))
            )
        )
    )
    with pytest.raises(ValueError):
        await MentorGeneratorService(client, "test").generate_mentor_response(
            "Olá", AsyncMock()
        )


@pytest.mark.anyio
async def test_generator_limits_tool_rounds():
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=Mock(
                    return_value=response(calls=[tool("consultar_trilha")])
                )
            )
        )
    )
    with pytest.raises(ValueError, match="Limite"):
        await MentorGeneratorService(client, "test").generate_mentor_response(
            "Olá", AsyncMock(return_value={})
        )
