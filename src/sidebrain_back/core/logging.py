import logging
import re

_SENSITIVE_QUERY = re.compile(
    r"(?i)(ticket|access_token|authorization)=([^&\s]+)"
)
_BEARER = re.compile(r"(?i)Bearer\s+[^\s,;]+")


def redact_sensitive_query(value: str) -> str:
    value = _SENSITIVE_QUERY.sub(r"\1=[REDACTED]", value)
    return _BEARER.sub("Bearer [REDACTED]", value)


class AccessLogRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_query(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                redact_sensitive_query(value)
                if isinstance(value, str)
                else value
                for value in record.args
            )
        return True


def configure_access_log_redaction() -> None:
    access_logger = logging.getLogger("uvicorn.access")
    if not any(
        isinstance(item, AccessLogRedactionFilter)
        for item in access_logger.filters
    ):
        access_logger.addFilter(AccessLogRedactionFilter())
