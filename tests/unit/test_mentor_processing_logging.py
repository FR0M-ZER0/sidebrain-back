from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from sidebrain_back.services import mentor_processing_service as processing


@pytest.mark.anyio
async def test_processing_logs_safe_error_details(monkeypatch, caplog):
    @asynccontextmanager
    async def lock(_user_id):
        yield Mock()

    context = Mock()
    context.get_mentor_message = AsyncMock(
        return_value={"mensagem": "mensagem privada"}
    )
    monkeypatch.setattr(processing, "mentor_user_lock", lock)
    monkeypatch.setattr(
        processing, "MentorContextService", Mock(return_value=context)
    )
    db = Mock()
    db.commit = AsyncMock()
    generator = Mock()
    generator.generate_mentor_response = AsyncMock(
        side_effect=ValueError("segredo do provedor")
    )
    service = processing.MentorProcessingService(db, generator)
    service.generations = Mock()
    service.generations.reserve = AsyncMock(
        return_value=Mock(attempt_id=uuid4())
    )
    service.generations.fail_attempt = AsyncMock()
    service.consent = Mock()
    service.consent._notice.return_value = ("versao", "provedor")
    service._check_lock_connection = AsyncMock()
    generation_id = uuid4()

    await service.process(uuid4(), generation_id)

    assert f"generation_id={generation_id}" in caplog.text
    assert "error_type=ValueError" in caplog.text
    assert "provider_status=None" in caplog.text
    assert "segredo do provedor" not in caplog.text
    assert "mensagem privada" not in caplog.text
