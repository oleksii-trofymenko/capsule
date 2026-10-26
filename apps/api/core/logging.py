"""Structured JSON logs on stdout, one object per line, with the request id of the current request.

Only `extra=` keys are allow-listed. `msg` and `exc` are free text, so callers must keep personal
data out of messages and exception text; review this when database writes land.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import TextIO

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# `extra=` keys that may appear in a log line. Keep them free of personal data.
ALLOWED_EXTRA = ("method", "path", "status", "duration_ms", "check", "error")

# Libraries that log URLs, queries or connection details at INFO/DEBUG; only warnings pass.
QUIET_LOGGERS = ("httpx", "httpcore", "psycopg", "sqlalchemy", "redis")

# uvicorn (ADR-021) installs its own text handlers before it calls the app factory. Its server
# loggers go through our JSON handler at LOG_LEVEL instead. Its access logger stays silent even
# without `--no-access-log`: RequestContextMiddleware writes the access line, without client IPs
# or query strings.
SERVER_LOGGERS = ("uvicorn", "uvicorn.error")
SERVER_ACCESS_LOGGER = "uvicorn.access"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for key in ALLOWED_EXTRA:
            if key in record.__dict__:
                payload[key] = record.__dict__[key]
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class JsonHandler(logging.StreamHandler[TextIO]):
    """The handler this module installs; a second call replaces it instead of adding one."""


def configure_logging(level: str) -> None:
    handler = JsonHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [h for h in root.handlers if not isinstance(h, JsonHandler)] + [handler]
    root.setLevel(level)
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    for name in SERVER_LOGGERS:
        server_logger = logging.getLogger(name)
        server_logger.handlers.clear()
        server_logger.setLevel(logging.NOTSET)
        server_logger.propagate = True
    access = logging.getLogger(SERVER_ACCESS_LOGGER)
    access.handlers.clear()
    access.propagate = False
