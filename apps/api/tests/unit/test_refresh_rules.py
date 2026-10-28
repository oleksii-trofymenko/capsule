"""The ADR-014 refresh state machine and the lock-timeout check, without a database."""

import psycopg.errors
import pytest
from sqlalchemy.exc import OperationalError

from core.db_errors import is_lock_timeout
from modules.auth.repository import TokenState
from modules.auth.service import Outcome, decide


def state(
    current_state: str = "rotated",
    *,
    grace_used: bool = False,
    in_window: bool = True,
    successor: str | None = "current",
) -> TokenState:
    return TokenState(current_state, grace_used, in_window, successor)


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        (state("current", in_window=False, successor=None), "rotate"),
        (state(), "grace"),
        (state(in_window=False), "reuse"),  # outside the 30 s window
        (state(grace_used=True), "reuse"),  # a second grace attempt
        (state(successor="rotated"), "reuse"),  # the successor was used
        (state(successor="superseded"), "reuse"),
        (state(successor=None), "reuse"),  # no successor row
        (state("superseded", successor=None), "reuse"),  # a superseded token comes back
        (state("superseded"), "reuse"),
    ],
    ids=[
        "current rotates",
        "grace",
        "outside window",
        "second grace",
        "successor used",
        "successor superseded",
        "no successor",
        "superseded token",
        "superseded with current successor",
    ],
)
def test_decide(token: TokenState, expected: Outcome) -> None:
    assert decide(token) == expected


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (OperationalError("SELECT", {}, psycopg.errors.LockNotAvailable()), True),
        (psycopg.errors.LockNotAvailable(), True),
        (OperationalError("SELECT", {}, psycopg.errors.QueryCanceled()), False),
        (OperationalError("SELECT", {}, OSError()), False),
        (RuntimeError(), False),
    ],
    ids=["wrapped 55P03", "bare 55P03", "statement timeout", "not psycopg", "not a db error"],
)
def test_is_lock_timeout(exc: BaseException, expected: bool) -> None:
    assert is_lock_timeout(exc) is expected
