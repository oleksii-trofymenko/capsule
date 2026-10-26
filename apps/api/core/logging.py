"""Structured JSON logs on stdout, one object per line, with the request id of the current request.

Only the fields listed here are emitted, so `extra=` cannot smuggle personal data into the logs.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import TextIO

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# `extra=` keys that may appear in a log line. Keep them free of personal data.
ALLOWED_EXTRA = ("method", "path", "status", "duration_ms", "check", "error", "failing")


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
