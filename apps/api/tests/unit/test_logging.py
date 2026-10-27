import asyncio
import json
import logging
import logging.config
import socket
import sys
from collections.abc import Iterator

import httpx
import psycopg
import pytest
import uvicorn
from sqlalchemy.exc import IntegrityError
from uvicorn.config import LOGGING_CONFIG

from core.logging import (
    QUIET_LOGGERS,
    SERVER_ACCESS_LOGGER,
    SERVER_LOGGERS,
    JsonFormatter,
    configure_logging,
    request_id_var,
)
from main import create_app
from tests.support import dummy_settings


def _record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord("capsule.test", logging.INFO, __file__, 1, "hello %s", ("x",), None)
    record.__dict__.update(extra)
    return record


def test_formats_one_json_object_with_the_request_id() -> None:
    token = request_id_var.set("req-1")
    try:
        line = JsonFormatter().format(_record(status=200, path="/v1/health"))
    finally:
        request_id_var.reset(token)

    payload = json.loads(line)
    assert payload["msg"] == "hello x"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "capsule.test"
    assert payload["request_id"] == "req-1"
    assert payload["status"] == 200
    assert payload["path"] == "/v1/health"
    assert payload["ts"].endswith("+00:00")


def test_drops_extra_fields_that_are_not_allowed() -> None:
    payload = json.loads(JsonFormatter().format(_record(email="someone@example.com")))

    assert "email" not in payload
    assert "someone@example.com" not in json.dumps(payload)
    assert payload["request_id"] is None


def test_includes_the_exception_trace() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            "capsule.test", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
        )

    payload = json.loads(JsonFormatter().format(record))
    assert "ValueError: boom" in payload["exc"]


def test_third_party_loggers_only_pass_warnings(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("DEBUG")

    logging.getLogger("httpx").info("HTTP Request: GET http://test/v1/ready?email=someone")
    logging.getLogger("psycopg.pool").debug("connection details")
    logging.getLogger("sqlalchemy.engine").info("SELECT 1")
    logging.getLogger("redis").warning("redis is slow")
    logging.getLogger("capsule.test").debug("own debug line")

    messages = [json.loads(line)["msg"] for line in capsys.readouterr().out.splitlines()]
    assert messages == ["redis is slow", "own debug line"]
    for name in QUIET_LOGGERS:
        assert logging.getLogger(name).getEffectiveLevel() == logging.WARNING


@pytest.fixture
def uvicorn_logging() -> Iterator[None]:
    """Apply uvicorn's own logging config, as `uvicorn` does before it calls the app factory."""
    names = (*SERVER_LOGGERS, SERVER_ACCESS_LOGGER)
    saved = {
        name: (
            logging.getLogger(name).handlers[:],
            logging.getLogger(name).level,
            logging.getLogger(name).propagate,
        )
        for name in names
    }
    logging.config.dictConfig(LOGGING_CONFIG)
    yield
    for name, (handlers, level, propagate) in saved.items():
        server_logger = logging.getLogger(name)
        server_logger.handlers[:] = handlers
        server_logger.setLevel(level)
        server_logger.propagate = propagate


@pytest.mark.usefixtures("uvicorn_logging")
def test_uvicorn_server_lines_are_json_at_our_level(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("WARNING")

    logging.getLogger("uvicorn.error").info("Started server process [%d]", 1)
    logging.getLogger("uvicorn.error").error("Application startup failed. Exiting.")

    captured = capsys.readouterr()
    lines = [json.loads(line) for line in captured.out.splitlines()]
    assert [(line["logger"], line["level"], line["msg"]) for line in lines] == [
        ("uvicorn.error", "ERROR", "Application startup failed. Exiting.")
    ]
    assert captured.err == ""


@pytest.mark.usefixtures("uvicorn_logging")
def test_uvicorn_access_lines_are_never_written(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("DEBUG")

    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d', "203.0.113.7:5000", "GET", "/v1/ready?email=someone", "1.1", 200
    )
    logging.getLogger("uvicorn.error").info("Started server process [%d]", 1)

    captured = capsys.readouterr()
    assert [json.loads(line)["msg"] for line in captured.out.splitlines()] == [
        "Started server process [1]"
    ]
    assert "203.0.113.7" not in captured.out + captured.err


PII = "someone@example.invalid"


def _integrity_error() -> IntegrityError:
    orig = psycopg.errors.UniqueViolation(f"duplicate key\nDETAIL: Key (email)=({PII}) exists")
    return IntegrityError("INSERT INTO t (email) VALUES (%(email)s)", {"email": PII}, orig)


def _raised(exc: BaseException) -> BaseException:
    try:
        raise exc
    except BaseException as caught:
        return caught


def _chained() -> BaseException:
    try:
        try:
            raise _integrity_error()
        except IntegrityError as exc:
            raise RuntimeError(f"wrapped: {exc}") from exc
    except RuntimeError as outer:
        return outer


IE = "IntegrityError (UniqueViolation)"
GROUP = _raised(ExceptionGroup("g", [_integrity_error()]))


@pytest.mark.parametrize(
    ("msg", "args", "exc", "field", "expected"),
    [
        ("failed", None, _raised(_integrity_error()), "exc", IE),
        ("failed: %s", (_integrity_error(),), None, "msg", f"failed: {IE}"),
        ("failed: %(e)s", ({"e": _integrity_error()},), None, "msg", f"failed: {IE}"),
        (_integrity_error(), None, None, "msg", IE),
        ("failed", None, _chained(), "exc", f"RuntimeError <- {IE}"),
        ("failed", None, GROUP, "exc", f"ExceptionGroup <- {IE}"),
        ("failed", None, _raised(psycopg.errors.UniqueViolation(PII)), "exc", "UniqueViolation"),
    ],
    ids=["exc_info", "arg", "mapping-arg", "msg", "chained", "group", "driver"],
)  # fmt: skip
def test_database_errors_are_described_never_printed(
    msg: object,
    args: tuple[object, ...] | None,
    exc: BaseException | None,
    field: str,
    expected: str,
) -> None:
    exc_info = (type(exc), exc, exc.__traceback__) if exc is not None else None
    # LogRecord turns a single mapping argument into the mapping, as logger.error() does.
    record = logging.LogRecord("capsule.test", logging.ERROR, __file__, 1, msg, args, exc_info)
    line = JsonFormatter().format(record)

    assert json.loads(line)[field] == expected
    assert PII not in line
    assert "INSERT" not in line
    assert "Traceback" not in line


def test_database_error_in_an_allowed_extra_is_described() -> None:
    line = JsonFormatter().format(_record(error=_integrity_error()))

    assert json.loads(line)["error"] == "IntegrityError (UniqueViolation)"
    assert PII not in line


ACCESS_FIELDS = ("method", "path", "status", "duration_ms")


@pytest.mark.anyio
@pytest.mark.usefixtures("uvicorn_logging")  # restores what uvicorn.Config's dictConfig changes
async def test_access_line_has_no_client_ip_or_query_under_real_uvicorn(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """R4: uvicorn with its access log switched on, as if `--no-access-log` were forgotten."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    config = uvicorn.Config(lambda: create_app(dummy_settings()), factory=True, lifespan="off")
    assert config.access_log
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        async with asyncio.timeout(5):
            while not server.started:  # noqa: ASYNC110 - uvicorn exposes only this flag
                await asyncio.sleep(0.01)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://127.0.0.1:{port}/v1/health?email={PII}",
                headers={"X-Forwarded-For": "203.0.113.7"},
            )
    finally:
        server.should_exit = True
        await task
        sock.close()

    assert response.status_code == 200
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert not [line for line in lines if line["logger"] == SERVER_ACCESS_LOGGER]
    access = [line for line in lines if line["msg"] == "request"]
    assert len(access) == 1
    assert set(access[0]) == {"ts", "level", "logger", "msg", "request_id", *ACCESS_FIELDS}
    assert access[0]["path"] == "/v1/health"
    raw = json.dumps(lines)
    assert PII not in raw
    assert "203.0.113.7" not in raw
    # uvicorn.error's startup line names the listening socket; no other line holds the IP.
    others = [line for line in lines if line["logger"] != "uvicorn.error"]
    assert "127.0.0.1" not in json.dumps(others)
