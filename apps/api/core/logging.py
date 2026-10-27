"""Structured JSON logs on stdout, one object per line, with the request id of the current request.

Only `extra=` keys are allow-listed. `msg` and `exc` are free text, so callers must keep personal
data out of messages and exception text. Database errors are the exception that is caught here
(ADR-022): in `exc_info`, as the message, as a log argument or as an `extra=` value, a database
error (or any exception chained to one, also inside lists, tuples, sets and dicts) is replaced
by its type, SQLSTATE and constraint name; a traceback keeps only frame locations. Messages that
a library built from such an error (asyncio's "Task exception was never retrieved") have every
`str()` and `repr()` of it replaced, and keep only their first line. Text a caller formats
itself before logging (an f-string with a truncated or reworded error) is not caught.
"""

import json
import logging
import sys
from collections.abc import Iterator, Mapping
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import TextIO

from core.db_errors import (
    describe_chain,
    describe_chain_with_frames,
    describe_db_error,
    exception_chain,
    involves_db_error,
)

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


# Containers in log arguments are searched this deep; anything deeper is printed as its type.
_MAX_DEPTH = 4


def _safe(value: object, depth: int = 0) -> object:
    if isinstance(value, BaseException):
        return describe_chain(value) if involves_db_error(value) else value
    if not isinstance(value, list | tuple | set | frozenset | dict):
        return value
    if depth >= _MAX_DEPTH:
        return f"<{type(value).__name__}>"
    if isinstance(value, dict):
        return {key: _safe(item, depth + 1) for key, item in value.items()}
    items = [_safe(item, depth + 1) for item in value]
    return items if isinstance(value, list) else tuple(items)


def _exceptions(value: object, depth: int = 0) -> Iterator[BaseException]:
    """Exceptions in a log argument, searched like `_safe` does."""
    if isinstance(value, BaseException):
        yield value
    elif depth < _MAX_DEPTH and isinstance(value, list | tuple | set | frozenset | dict):
        for item in value.values() if isinstance(value, dict) else value:
            yield from _exceptions(item, depth + 1)


def _db_errors(record: logging.LogRecord) -> list[BaseException]:
    """Every exception chained to a database error in `exc_info`, the message or an argument."""
    roots = [record.msg, record.args]
    if record.exc_info and record.exc_info[1] is not None:
        roots.append(record.exc_info[1])
    found: list[BaseException] = []
    for root in roots:
        for exc in _exceptions(root):
            if involves_db_error(exc):
                found.extend(exception_chain(exc))
    return found


def _message(record: logging.LogRecord) -> str:
    """`record.getMessage()` with database errors described instead of printed."""
    msg = str(_safe(record.msg))
    args = record.args
    if isinstance(args, Mapping):
        msg = msg % {key: _safe(value, 1) for key, value in args.items()}
    elif args:
        msg = msg % tuple(_safe(value, 1) for value in args)
    for error in _db_errors(record):
        for text in (repr(error), str(error)):
            if text:
                msg = msg.replace(text, describe_db_error(error))
    exc = record.exc_info[1] if record.exc_info else None
    if exc is not None and involves_db_error(exc):
        # A library may have quoted the error in a form not matched above; DETAIL and the
        # statement start on later lines of the driver message.
        msg = msg.split("\n", 1)[0]
    return msg


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": _message(record),
            "request_id": request_id_var.get(),
        }
        for key in ALLOWED_EXTRA:
            if key in record.__dict__:
                payload[key] = _safe(record.__dict__[key])
        if record.exc_info:
            exc = record.exc_info[1]
            if exc is not None and involves_db_error(exc):
                payload["exc"] = describe_chain_with_frames(exc)
            else:
                payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class JsonHandler(logging.StreamHandler[TextIO]):
    """The handler this module installs; a second call replaces it instead of adding one."""

    def handleError(self, record: logging.LogRecord) -> None:  # noqa: N802 - logging's name
        """A record that cannot be formatted. The default prints `msg` and `args` to stderr,
        which may hold the very values the formatter keeps out; this line names only where."""
        error = sys.exc_info()[1]
        line = {
            "level": "ERROR",
            "logger": "capsule.logging",
            "msg": "log record could not be formatted",
            "source_logger": record.name,
            "where": f"{record.pathname}:{record.lineno}",
            "error": type(error).__name__ if error is not None else None,
        }
        try:
            self.stream.write(json.dumps(line) + "\n")
            self.flush()
        except Exception:  # noqa: S110 - nowhere left to report; never raise from logging
            pass


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
