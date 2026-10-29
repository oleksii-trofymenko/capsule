"""The deletion ledger against real Postgres (ADR-022): the row lives in the caller's transaction,
the file line matches it, and an unusable directory never stops `api` from starting."""

import json
import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from core.db import create_engine, create_sessionmaker
from core.deletion_ledger import FILE_NAME, DeletionLedger
from main import create_app
from tests.integration.conftest import checked_database_url
from tests.support import TEST_SIGNING_KEYS, client_for

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


def _settings(**overrides: object) -> Settings:
    checked_database_url()
    settings = Settings.from_env(os.environ, signing_keys=TEST_SIGNING_KEYS)
    return settings.model_copy(update=overrides)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_engine(_settings())
    try:
        async with create_sessionmaker(engine)() as session:
            yield session
    finally:
        await engine.dispose()


async def _rows(session: AsyncSession, principal_id: uuid.UUID) -> list[tuple[object, ...]]:
    async with session.begin():
        result = await session.execute(
            text("SELECT principal_id, deleted_at FROM deletion_ledger WHERE principal_id = :id"),
            {"id": principal_id},
        )
        return [tuple(row) for row in result]


async def test_row_is_written_in_the_callers_transaction_and_the_file_matches_it(
    session: AsyncSession, tmp_path: Path
) -> None:
    ledger = DeletionLedger(tmp_path)
    principal_id = uuid.uuid4()
    try:
        async with session.begin():
            entry = await ledger.record(session, principal_id)
        await ledger.append(entry)
    finally:
        ledger.close()

    assert await _rows(session, principal_id) == [(principal_id, entry.deleted_at)]
    line = (tmp_path / FILE_NAME).read_text(encoding="ascii")
    assert line == f"{principal_id} {entry.deleted_at.isoformat()}\n"
    assert line.split(" ")[1].endswith("+00:00\n")


async def test_row_rolls_back_with_the_callers_transaction(session: AsyncSession) -> None:
    ledger = DeletionLedger(None)
    principal_id = uuid.uuid4()
    try:
        with pytest.raises(RuntimeError):
            async with session.begin():
                await ledger.record(session, principal_id)
                raise RuntimeError("the deletion failed later in the transaction")
    finally:
        ledger.close()

    assert await _rows(session, principal_id) == []


async def test_api_starts_and_is_ready_with_a_missing_ledger_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "not-mounted"
    app = create_app(_settings(deletion_ledger_dir=missing))  # after capsys: logs are captured

    async with client_for(app, lifespan=True) as client:
        response = await client.get("/v1/ready")

    assert response.status_code == 200, response.text
    assert not missing.exists()  # never created
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    [error] = [line for line in lines if line.get("event") == "ledger_directory_unusable"]
    assert error["level"] == "ERROR"
    assert error["reason"] == "missing"
    assert str(tmp_path) not in json.dumps(error)  # no path in the log line
