import json
import logging
import sys

import pytest

from core.logging import QUIET_LOGGERS, JsonFormatter, configure_logging, request_id_var


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
