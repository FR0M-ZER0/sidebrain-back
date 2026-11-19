import logging

from sidebrain_back.core.logging import AccessLogRedactionFilter


def test_access_log_redacts_ticket_and_bearer_query_values():
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        0,
        '%s - "WebSocket %s" %s',
        (
            "127.0.0.1",
            "/api/v1/ws?ticket=secret-value&access_token=bearer-value",
            "Bearer header-secret",
        ),
        None,
    )

    assert AccessLogRedactionFilter().filter(record)

    rendered = record.getMessage()
    assert "secret-value" not in rendered
    assert "bearer-value" not in rendered
    assert "header-secret" not in rendered
    assert "ticket=[REDACTED]" in rendered
