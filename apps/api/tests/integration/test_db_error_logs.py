"""ADR-022: a real unique violation reaches the log as type, SQLSTATE and constraint only."""

import json
import logging
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, pool, text
from sqlalchemy.exc import IntegrityError

from core.logging import JsonFormatter
from tests.integration.conftest import checked_database_url

pytestmark = pytest.mark.integration

PII = "someone@example.invalid"
EXPECTED = "IntegrityError (UniqueViolation); sqlstate=23505; constraint=e105d_email_key"


@pytest.fixture
def violation() -> Iterator[IntegrityError]:
    # Default engine options on purpose: the statement and bound values are in str(exc).
    engine = create_engine(checked_database_url(), poolclass=pool.NullPool)
    with engine.connect() as conn:
        conn.execute(text("CREATE TEMP TABLE e105d (email text CONSTRAINT e105d_email_key UNIQUE)"))
        insert = text("INSERT INTO e105d (email) VALUES (:email)")
        conn.execute(insert, {"email": PII})
        with pytest.raises(IntegrityError) as caught:
            conn.execute(insert, {"email": PII})
    engine.dispose()
    assert PII in str(caught.value)  # what would leak without the formatter
    yield caught.value


def _line(msg: str, args: tuple[object, ...] | None, exc: BaseException | None) -> str:
    exc_info = (type(exc), exc, exc.__traceback__) if exc is not None else None
    record = logging.LogRecord("capsule.test", logging.ERROR, __file__, 1, msg, args, exc_info)
    return JsonFormatter().format(record)


def test_unique_violation_as_exc_info(violation: IntegrityError) -> None:
    line = _line("insert failed", None, violation)

    assert json.loads(line)["exc"] == EXPECTED
    assert PII not in line
    assert "DETAIL" not in line


def test_unique_violation_as_log_argument(violation: IntegrityError) -> None:
    line = _line("insert failed: %s", (violation,), None)

    assert json.loads(line)["msg"] == f"insert failed: {EXPECTED}"
    assert PII not in line
    assert "DETAIL" not in line
