import asyncio
import gc
import io
import json
import logging
import sys

import psycopg
import pytest
from sqlalchemy.exc import IntegrityError

from core.logging import (
    QUIET_LOGGERS,
    JsonFormatter,
    JsonHandler,
    configure_logging,
    request_id_var,
)


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
        ("failed: %s", ([_integrity_error()],), None, "msg", f"failed: ['{IE}']"),
        ("failed: %s", ({"k": (_integrity_error(),)},), None, "msg", f"failed: {{'k': ('{IE}',)}}"),
    ],
    ids=["exc_info", "arg", "mapping-arg", "msg", "chained", "group", "driver", "list", "nested"],
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

    assert json.loads(line)[field].split("\n")[0] == expected
    assert PII not in line
    assert "INSERT" not in line
    assert "Traceback" not in line


def test_database_error_in_an_allowed_extra_is_described() -> None:
    deep: list[object] = [_integrity_error()]
    for _ in range(10):
        deep = [deep]
    line = JsonFormatter().format(_record(error={"e": _integrity_error(), "deep": deep}))

    # The dict is depth 0; a container at depth 4 prints as its type.
    assert json.loads(line)["error"] == {"e": IE, "deep": [[["<list>"]]]}
    assert PII not in line


def test_database_traceback_keeps_frame_locations_only() -> None:
    exc = json.loads(JsonFormatter().format(_record(exc_info=_exc_info(_chained()))))["exc"]

    assert exc.startswith(f"RuntimeError <- {IE}\nRuntimeError raised at:\n")
    assert "test_logging.py" in exc
    assert ", in _chained" in exc
    assert PII not in exc
    assert "DETAIL" not in exc


def _exc_info(exc: BaseException) -> tuple[type[BaseException], BaseException, object]:
    return type(exc), exc, exc.__traceback__


def test_prebuilt_message_quoting_the_error_is_rewritten() -> None:
    error = _raised(_integrity_error())
    record = _record(exc_info=_exc_info(error))
    record.msg, record.args = f"future: <Task exception={error!r}> after {error}", None

    line = JsonFormatter().format(record)

    assert json.loads(line)["msg"] == f"future: <Task exception={IE}> after {IE}"
    assert PII not in line


def test_unretrieved_task_error_from_asyncio_is_described(
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def insert() -> None:
        raise _integrity_error()

    configure_logging("INFO")
    loop = asyncio.new_event_loop()
    try:
        task = loop.create_task(insert())
        loop.run_until_complete(asyncio.sleep(0))
        del task  # never awaited: asyncio logs "Task exception was never retrieved"
        gc.collect()
    finally:
        loop.close()

    out = capsys.readouterr().out
    line = next(json.loads(raw) for raw in out.splitlines() if '"asyncio"' in raw)
    assert line["msg"] == "Task exception was never retrieved"
    assert line["exc"].startswith(IE)
    assert PII not in out
    assert "DETAIL" not in out


def test_a_record_that_cannot_be_formatted_names_only_where(
    capsys: pytest.CaptureFixture[str],
) -> None:
    stream = io.StringIO()
    handler = JsonHandler(stream)
    handler.setFormatter(JsonFormatter())
    log = logging.getLogger("capsule.test.broken")
    log.addHandler(handler)
    log.propagate = False
    try:
        log.error("x: %s %s", _integrity_error())  # one argument for two placeholders
    finally:
        log.removeHandler(handler)
        log.propagate = True

    line = json.loads(stream.getvalue())
    assert line["source_logger"] == "capsule.test.broken"
    assert line["where"].endswith(f"test_logging.py:{line['where'].rsplit(':', 1)[1]}")
    assert line["error"] == "TypeError"
    assert PII not in stream.getvalue() + capsys.readouterr().err
