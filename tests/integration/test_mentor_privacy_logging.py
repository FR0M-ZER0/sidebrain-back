import logging

import pytest
from sqlalchemy import text

from sidebrain_back.core.database import engine


@pytest.mark.anyio
async def test_database_debug_logging_hides_sensitive_parameters(
    db_session, caplog
):
    secret = "conteudo-sintetico-privado-sdb110"
    previous = engine.echo
    try:
        engine.echo = True
        with caplog.at_level(logging.INFO, logger="sqlalchemy.engine.Engine"):
            await db_session.execute(
                text("SELECT CAST(:value AS text)"), {"value": secret}
            )
        assert secret not in caplog.text
    finally:
        engine.echo = previous
