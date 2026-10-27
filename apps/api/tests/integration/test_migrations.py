"""Alembic against real Postgres (ADR-007, ADR-016), each test on its own throwaway database."""

import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
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


def test_upgrade_head_twice_changes_nothing(fresh_database: str) -> None:
    config = alembic_config()

    command.upgrade(config, "head")
    command.upgrade(config, "head")

    assert _current_heads(fresh_database) == _head()
