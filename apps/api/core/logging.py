"""Structured JSON logs on stdout, one object per line, with the request id of the current request.

Only `extra=` keys are allow-listed. `msg` and `exc` are free text, so callers must keep personal
data out of messages and exception text. Database errors are the exception that is caught here
(ADR-022): in `exc_info`, as the message, as a log argument or as an `extra=` value, a database
error (or any exception chained to one, also inside list, tuple, set and dict keys and values,
and in a finished asyncio Future or Task) is replaced by its type, SQLSTATE and constraint name;
a traceback keeps only frame locations. Values without one pass through unchanged. In the final
message, every `str()` and `repr()` of those database errors is replaced too (asyncio's "Task
exception was never retrieved"), and with a database `exc_info` only the first line is kept.
Not caught: text a caller formats itself (an f-string with a truncated or reworded error), and
other objects that embed an exception in their own `repr`.
"""

import asyncio
import json
import logging
import re
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
    is_db_error,
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


# Containers in log arguments are searched this deep. A value with containers nested deeper is
# rebuilt as if it held a database error, and the deepest level prints as its type.
_MAX_DEPTH = 8
_CONTAINERS = (list, tuple, set, frozenset, dict)


def _held(value: object) -> BaseException | None:
    """The exception a value is or carries: a done, not-cancelled Future or Task holds one."""
    if isinstance(value, BaseException):
        return value
    if isinstance(value, asyncio.Future) and value.done() and not value.cancelled():
        # exception() marks the future retrieved: asyncio's own "never retrieved" warning will
        # not fire for it later.
        return value.exception()
    return None


def _items(value: object) -> list[object]:
    if isinstance(value, dict):
        return [*value.keys(), *value.values()]
    return list(value) if isinstance(value, _CONTAINERS) else []


def _exceptions(value: object, depth: int = 0) -> Iterator[BaseException]:
    held = _held(value)
    if held is not None:
        yield held
    elif depth < _MAX_DEPTH:
        for item in _items(value):
            yield from _exceptions(item, depth + 1)


def _needs_rebuild(value: object, depth: int) -> bool:
    """True if the value holds a database error, or nests containers past the search depth."""
    held = _held(value)
    if held is not None:
        return involves_db_error(held)
    if not isinstance(value, _CONTAINERS):
        return False
    if depth >= _MAX_DEPTH:
        return True
    return any(_needs_rebuild(item, depth + 1) for item in _items(value))


def _safe(value: object, depth: int = 0) -> object:
    """The value itself unless it holds a database error; then a copy with each described."""
    if not _needs_rebuild(value, depth):
        return value
    if isinstance(value, BaseException):
        return describe_chain(value)
    if not isinstance(value, _CONTAINERS):
        return value  # a Future: its repr quotes the error, which _message replaces
    if depth >= _MAX_DEPTH:
        return f"<{type(value).__name__}>"
    if isinstance(value, dict):
        return {_safe(k, depth + 1): _safe(v, depth + 1) for k, v in value.items()}
    items = [_safe(item, depth + 1) for item in value]
    # The base type: a subclass such as a named tuple may not take one iterable argument.
    return next(t for t in (list, tuple, set, frozenset) if isinstance(value, t))(items)


def _db_texts(record: logging.LogRecord) -> dict[str, str]:
    """`str()` and `repr()` of every database error (and its driver error) the record carries,
    mapped to the description that replaces it."""
    roots = [record.msg, record.args]
    if record.exc_info and record.exc_info[1] is not None:
        roots.append(record.exc_info[1])
    texts: dict[str, str] = {}
    for found in (exc for root in roots for exc in _exceptions(root)):
        for error in exception_chain(found):
            if not is_db_error(error):
                continue
            for e in (error, getattr(error, "orig", None)):
                if isinstance(e, BaseException):
                    for text in (repr(e), str(e)):
                        if text:
                            texts.setdefault(text, describe_db_error(e))
    return texts


def _message(record: logging.LogRecord) -> str:
    """`record.getMessage()` with database errors described instead of printed."""
    msg = str(_safe(record.msg))
    args = record.args
    if isinstance(args, Mapping):
        msg = msg % _safe(dict(args))  # keys too: `log.error("%s", {exc: 1})` lands here
    elif args:
        msg = msg % tuple(_safe(value, 1) for value in args)
    texts = _db_texts(record)
    if texts:
        # One pass, longest first, so inserted descriptions are never matched again.
        pattern = "|".join(map(re.escape, sorted(texts, key=len, reverse=True)))
        msg = re.sub(pattern, lambda match: texts[match.group(0)], msg)
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
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": "ERROR",
            "logger": "capsule.logging",
            "msg": "log record could not be formatted",
            "source_logger": record.name,
            "where": f"{record.pathname}:{record.lineno}",
            "error": type(error).__name__ if error is not None else None,
            "request_id": request_id_var.get(),
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
