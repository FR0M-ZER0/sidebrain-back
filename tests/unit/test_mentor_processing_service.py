from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from sidebrain_back.services import mentor_processing_service as processing


@pytest.mark.anyio
async def test_processing_always_supplies_history_to_generator(monkeypatch):
    @asynccontextmanager
    async def lock(_user_id):
        yield Mock()

    user_id = uuid4()
    generation_id = uuid4()
    base = {"mensagem": "Exatamente, este é o título"}
    history = [
        {
            "role": "student",
            "content": "A lição é Listas e primeiros resumos.",
        },
        {"role": "mentor", "content": "Esse é o título completo?"},
    ]
    context = Mock()
    context.get_mentor_message = AsyncMock(return_value=base)
    context.get_mentor_tool_data = AsyncMock(
        return_value={"historico": history}
    )
    monkeypatch.setattr(processing, "mentor_user_lock", lock)
    monkeypatch.setattr(
        processing, "MentorContextService", Mock(return_value=context)
    )
    db = Mock()
    db.commit = AsyncMock()
    generator = Mock()
    generator.generate_mentor_response = AsyncMock(return_value="Vamos lá.")
    service = processing.MentorProcessingService(db, generator)
    service.generations = Mock()
    service.generations.reserve = AsyncMock(
        return_value=Mock(attempt_id=uuid4())
    )
    service.generations.complete = AsyncMock()
    service.consent = Mock()
    service.consent._notice.return_value = ("versao", "provedor")
    service._check_lock_connection = AsyncMock()

    await service.process(user_id, generation_id)

    context.get_mentor_tool_data.assert_awaited_once_with(
        user_id, base, "consultar_historico"
    )
    args, kwargs = generator.generate_mentor_response.await_args
    assert args[0] == base["mensagem"]
    assert callable(args[1])
    assert kwargs["history"] == history
