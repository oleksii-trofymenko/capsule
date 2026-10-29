"""The deletion ledger (ADR-022): the one writer for every deleted principal.

`record` inserts the row in the caller's transaction; the table is the record. After commit,
`append` adds `<principal id> <deletion time, ISO-8601 UTC>` to `deletion-ledger.txt` in the
configured directory, on the external disk. A restore replays the union of both (E1-23).

The directory is never created here, so a missing mount cannot write into the container. An
unset, missing or unwritable directory never fails a request or the start-up: the error is
logged with the principal id and the error type only.
"""

import asyncio
import logging
import os
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

FILE_NAME = "deletion-ledger.txt"  # E1-23 reconciles and prunes this file by name
TIMEOUT_S = 2.0  # a stalled USB disk must not hold a request

logger = logging.getLogger(__name__)

_INSERT = text("INSERT INTO deletion_ledger (principal_id) VALUES (:id) RETURNING deleted_at")


class LedgerDirectoryUnsetError(Exception):
    """DELETION_LEDGER_DIR is not set."""


@dataclass(frozen=True)
class LedgerEntry:
    principal_id: uuid.UUID
    deleted_at: datetime

    def line(self) -> str:
        return f"{self.principal_id} {self.deleted_at.astimezone(UTC).isoformat()}\n"


def _write(directory: Path | None, line: str) -> None:
    if directory is None:
        raise LedgerDirectoryUnsetError
    # Mode "a" creates the file but never the directory.
    with (directory / FILE_NAME).open("a", encoding="ascii", newline="\n") as file:
        file.write(line)
        file.flush()
        os.fsync(file.fileno())


def _directory_problem(directory: Path | None) -> str | None:
    if directory is None:
        return "unset"
    if not directory.exists():
        return "missing"
    if not directory.is_dir():
        return "not_a_directory"
    if not os.access(directory, os.W_OK | os.X_OK):
        return "not_writable"
    return None


class DeletionLedger:
    """One per app (`app.state.deletion_ledger`). File I/O runs on its own single thread, so
    appends are serialised and a hung disk never blocks the event loop."""

    def __init__(self, directory: Path | None, timeout_s: float = TIMEOUT_S) -> None:
        self._directory = directory
        self._timeout_s = timeout_s
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="deletion-ledger")

    async def record(self, session: AsyncSession, principal_id: uuid.UUID) -> LedgerEntry:
        """Call inside the transaction that deletes the principal; it rolls back with it."""
        deleted_at: datetime = (await session.execute(_INSERT, {"id": principal_id})).scalar_one()
        return LedgerEntry(principal_id, deleted_at)

    async def append(self, entry: LedgerEntry) -> None:
        """Call after commit. Never raises; a failure is logged and the table stays the record."""
        try:
            await self._run(_write, self._directory, entry.line())
        except Exception as exc:
            logger.error(
                "deletion ledger append failed",
                extra={
                    "event": "ledger_append_failed",
                    "principal_id": str(entry.principal_id),
                    "error": type(exc).__name__,
                },
            )

    async def check_directory(self) -> None:
        """At start-up: log an unusable directory, never raise."""
        try:
            problem = await self._run(_directory_problem, self._directory)
        except Exception as exc:
            problem = type(exc).__name__
        if problem is not None:
            logger.error(
                "deletion ledger directory unusable",
                extra={"event": "ledger_directory_unusable", "reason": problem},
            )

    def close(self) -> None:
        # Queued appends are dropped (each already timed out or logged); a running one finishes.
        self._executor.shutdown(wait=False, cancel_futures=True)

    async def _run[T](self, func: Callable[..., T], *args: object) -> T:
        # On timeout the wrapped future is cancelled: a queued call never runs, a running one
        # finishes in its thread, unawaited.
        future = asyncio.wrap_future(self._executor.submit(func, *args))
        return await asyncio.wait_for(future, self._timeout_s)
