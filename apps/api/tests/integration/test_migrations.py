"""Alembic against real Postgres (ADR-007, ADR-016), each test on its own throwaway database."""

import shutil
import textwrap
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, pool, text
from sqlalchemy.engine import make_url

from tests.integration.conftest import checked_database_url
from tests.support import ALEMBIC_INI, alembic_config

pytestmark = pytest.mark.integration


@pytest.fixture
def fresh_database(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """An empty `capsule_mig_<uuid>_test` database next to the test one, dropped afterwards."""
    base = make_url(checked_database_url())
    name = f"capsule_mig_{uuid.uuid4().hex}_test"  # 49 chars, under Postgres's 63
    admin = create_engine(base, poolclass=pool.NullPool, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = base.set(database=name).render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", url)
    try:
        yield url
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def _current_heads(url: str) -> tuple[str, ...]:
    engine = create_engine(url, poolclass=pool.NullPool)
    try:
        with engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_heads()
    finally:
        engine.dispose()


def _head() -> tuple[str, ...]:
    return tuple(ScriptDirectory.from_config(alembic_config()).get_heads())


def test_upgrade_downgrade_upgrade_round_trip(fresh_database: str) -> None:
    config = alembic_config()

    command.upgrade(config, "head")
    assert _current_heads(fresh_database) == _head()

    command.downgrade(config, "base")
    assert _current_heads(fresh_database) == ()

    command.upgrade(config, "head")
    assert _current_heads(fresh_database) == _head()


FAILING_MIGRATION = """
from alembic import op

revision = "f0000000fail"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TABLE people (email text CONSTRAINT people_email_key UNIQUE)")
    op.execute("INSERT INTO people VALUES ('secret@example.invalid'), ('secret@example.invalid')")


def downgrade() -> None:
    pass
"""


def test_failed_migration_reports_no_row_values(fresh_database: str, tmp_path: Path) -> None:
    # The real env.py, with one migration that hits a unique violation (ADR-022).
    (tmp_path / "versions").mkdir()
    shutil.copy(ALEMBIC_INI.parent / "migrations" / "env.py", tmp_path / "env.py")
    (tmp_path / "versions" / "f0000000fail_unique.py").write_text(FAILING_MIGRATION)
    config = alembic_config()
    config.set_main_option("script_location", str(tmp_path))

    with pytest.raises(SystemExit) as caught:
        command.upgrade(config, "head")

    message = str(caught.value)
    assert message == (
        "migration failed: IntegrityError (UniqueViolation); "
        "sqlstate=23505; constraint=people_email_key"
    )
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    # One transaction: the table from the first statement is gone too.
    engine = create_engine(fresh_database, poolclass=pool.NullPool)
    try:
        with engine.connect() as conn:
            assert conn.execute(text("SELECT to_regclass('people')")).scalar() is None
    finally:
        engine.dispose()


def _scripts_with(tmp_path: Path, upgrade_body: str) -> Config:
    """The real env.py with a single migration whose `upgrade()` runs `upgrade_body`."""
    (tmp_path / "versions").mkdir()
    shutil.copy(ALEMBIC_INI.parent / "migrations" / "env.py", tmp_path / "env.py")
    migration = (
        "from alembic import op\n\n"
        'revision = "f0000000lock"\n'
        "down_revision = None\n"
        "branch_labels = None\n"
        "depends_on = None\n\n\n"
        f"def upgrade() -> None:\n{textwrap.indent(textwrap.dedent(upgrade_body), '    ')}\n\n"
        "def downgrade() -> None:\n    pass\n"
    )
    (tmp_path / "versions" / "f0000000lock_test.py").write_text(migration)
    config = alembic_config()
    config.set_main_option("script_location", str(tmp_path))
    return config


def _scalar(url: str, sql: str) -> object:
    engine = create_engine(url, poolclass=pool.NullPool)
    try:
        with engine.connect() as conn:
            return conn.execute(text(sql)).scalar()
    finally:
        engine.dispose()


RECORD_LOCK_TIMEOUT = (
    "op.execute(\"CREATE TABLE seen AS SELECT current_setting('lock_timeout') AS v\")"
)


@pytest.mark.parametrize(
    ("upgrade_body", "expected"),
    [
        pytest.param(RECORD_LOCK_TIMEOUT, "5s", id="default"),
        pytest.param(
            f"op.execute(\"SET LOCAL lock_timeout = '30s'\")\n{RECORD_LOCK_TIMEOUT}",
            "30s",
            id="set-local-override",
        ),
        pytest.param(
            f"with op.get_context().autocommit_block():\n    {RECORD_LOCK_TIMEOUT}",
            "5s",
            id="autocommit-block",
        ),
    ],
)
def test_migrations_run_with_a_lock_timeout(
    fresh_database: str, tmp_path: Path, upgrade_body: str, expected: str
) -> None:
    command.upgrade(_scripts_with(tmp_path, upgrade_body), "head")

    assert _scalar(fresh_database, "SELECT v FROM seen") == expected


def test_migration_blocked_on_a_lock_fails_fast_and_rolls_back(
    fresh_database: str, tmp_path: Path
) -> None:
    config = _scripts_with(
        tmp_path,
        """
        op.execute("CREATE TABLE made_first (id int)")
        op.execute("ALTER TABLE held ADD COLUMN added int")
        """,
    )
    blocker = create_engine(fresh_database, poolclass=pool.NullPool)
    try:
        with blocker.connect() as conn:
            conn.execute(text("CREATE TABLE held (id int)"))
            conn.commit()
            # Without lock_timeout the migration would wait forever: release the lock after 20 s
            # instead, so a regression fails the assertions below rather than hanging.
            conn.execute(text("SET idle_in_transaction_session_timeout = '20s'"))
            # A long-running reader: ALTER TABLE needs ACCESS EXCLUSIVE and must wait for it.
            conn.execute(text("LOCK TABLE held IN ACCESS SHARE MODE"))
            started = time.monotonic()
            with pytest.raises(SystemExit) as caught:
                command.upgrade(config, "head")
            elapsed = time.monotonic() - started
            conn.rollback()
    finally:
        blocker.dispose()

    assert str(caught.value) == (
        "migration failed: OperationalError (LockNotAvailable); sqlstate=55P03"
    )
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    assert 4.5 <= elapsed < 15, f"gave up after {elapsed:.2f} s"
    # One transaction: nothing of the run is left, not even the version table.
    assert _scalar(fresh_database, "SELECT to_regclass('made_first')") is None
    assert _scalar(fresh_database, "SELECT to_regclass('alembic_version')") is None
    columns = "SELECT count(*) FROM information_schema.columns WHERE table_name = 'held'"
    assert _scalar(fresh_database, columns) == 1


def test_upgrade_head_twice_changes_nothing(fresh_database: str) -> None:
    config = alembic_config()

    command.upgrade(config, "head")
    command.upgrade(config, "head")

    assert _current_heads(fresh_database) == _head()
