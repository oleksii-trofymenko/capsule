"""The deletion-ledger file writer (ADR-022): line format and every failure path, no database."""

import logging
import threading
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from core import deletion_ledger
from core.deletion_ledger import FILE_NAME, DeletionLedger, LedgerEntry

pytestmark = pytest.mark.anyio

PRINCIPAL = uuid.UUID("0b7f3c1e-58a4-4d4e-9f43-2c6d1a7e9b10")
DELETED_AT = datetime(2026, 10, 29, 9, 30, 15, 123456, tzinfo=UTC)
ENTRY = LedgerEntry(PRINCIPAL, DELETED_AT)


@pytest.fixture
def ledger_for() -> Iterator[list[DeletionLedger]]:
    made: list[DeletionLedger] = []
    yield made
    for ledger in made:
        ledger.close()


def _ledger(made: list[DeletionLedger], directory: Path | None, **kw: float) -> DeletionLedger:
    ledger = DeletionLedger(directory, **kw)
    made.append(ledger)
    return ledger


def _errors(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "core.deletion_ledger"]


def test_line_is_the_id_and_the_utc_deletion_time() -> None:
    assert ENTRY.line() == f"{PRINCIPAL} 2026-10-29T09:30:15.123456+00:00\n"


def test_line_converts_another_offset_to_utc() -> None:
    local = DELETED_AT.astimezone(timezone(timedelta(hours=2)))

    assert LedgerEntry(PRINCIPAL, local).line() == ENTRY.line()


async def test_append_adds_one_line_per_entry(
    tmp_path: Path, ledger_for: list[DeletionLedger], caplog: pytest.LogCaptureFixture
) -> None:
    ledger = _ledger(ledger_for, tmp_path)
    other = LedgerEntry(uuid.uuid4(), DELETED_AT)

    await ledger.append(ENTRY)
    await ledger.append(other)

    content = (tmp_path / FILE_NAME).read_text(encoding="ascii")
    assert content == ENTRY.line() + other.line()
    assert _errors(caplog) == []


@pytest.mark.parametrize("case", ["unset", "missing", "a_file"])
async def test_failed_append_logs_the_id_and_type_only_and_never_raises(
    case: str,
    tmp_path: Path,
    ledger_for: list[DeletionLedger],
    caplog: pytest.LogCaptureFixture,
) -> None:
    directory: Path | None = {
        "unset": None,
        "missing": tmp_path / "missing",
        "a_file": tmp_path / "a-file",
    }[case]
    if case == "a_file":
        (tmp_path / "a-file").write_text("not a directory", encoding="ascii")
    ledger = _ledger(ledger_for, directory)

    await ledger.append(ENTRY)  # no exception

    [record] = _errors(caplog)
    assert record.levelno == logging.ERROR
    assert record.getMessage() == "deletion ledger append failed"
    assert record.__dict__["principal_id"] == str(PRINCIPAL)
    assert record.__dict__["event"] == "ledger_append_failed"
    expected = {
        "unset": {"LedgerDirectoryUnsetError"},
        "missing": {"FileNotFoundError"},
        "a_file": {"NotADirectoryError", "FileNotFoundError"},  # Linux, Windows
    }[case]
    assert record.__dict__["error"] in expected
    assert not (tmp_path / "missing").exists()  # the directory is never created


async def test_a_stalled_disk_times_out_and_logs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    ledger_for: list[DeletionLedger],
    caplog: pytest.LogCaptureFixture,
) -> None:
    release = threading.Event()

    def stalled(*_: object) -> None:
        release.wait(5)

    monkeypatch.setattr(deletion_ledger, "_write", stalled)
    ledger = _ledger(ledger_for, tmp_path, timeout_s=0.05)

    started = time.monotonic()
    await ledger.append(ENTRY)
    elapsed = time.monotonic() - started
    release.set()

    assert elapsed < 1.0
    [record] = _errors(caplog)
    assert record.__dict__["error"] == "TimeoutError"
    assert record.__dict__["principal_id"] == str(PRINCIPAL)


@pytest.mark.parametrize("case", ["unset", "missing", "a_file"])
async def test_start_up_check_logs_an_unusable_directory(
    case: str,
    tmp_path: Path,
    ledger_for: list[DeletionLedger],
    caplog: pytest.LogCaptureFixture,
) -> None:
    directory = {"unset": None, "missing": tmp_path / "missing", "a_file": tmp_path / "f"}[case]
    if case == "a_file":
        (tmp_path / "f").write_text("x", encoding="ascii")

    await _ledger(ledger_for, directory).check_directory()  # no exception

    [record] = _errors(caplog)
    assert record.levelno == logging.ERROR
    assert record.__dict__["event"] == "ledger_directory_unusable"
    reason = {"unset": "unset", "missing": "missing", "a_file": "not_a_directory"}[case]
    assert record.__dict__["reason"] == reason
    assert "principal_id" not in record.__dict__


async def test_start_up_check_is_silent_for_a_writable_directory(
    tmp_path: Path, ledger_for: list[DeletionLedger], caplog: pytest.LogCaptureFixture
) -> None:
    await _ledger(ledger_for, tmp_path).check_directory()

    assert _errors(caplog) == []
    assert not (tmp_path / FILE_NAME).exists()  # the check writes nothing
