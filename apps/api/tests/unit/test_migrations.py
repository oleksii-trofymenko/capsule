"""Alembic checks that need no database."""

import pytest
from alembic import command
from alembic.script import ScriptDirectory

from core.config import ConfigError
from tests.support import alembic_config


def test_revision_history_has_a_single_head() -> None:
    # Two heads mean two branches added migrations in parallel: merge them before shipping.
    heads = ScriptDirectory.from_config(alembic_config()).get_heads()

    assert len(heads) == 1, f"expected one head, got {heads}"


def test_upgrade_without_database_url_fails_before_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ConfigError, match="DATABASE_URL"):
        command.upgrade(alembic_config(), "head")


def test_upgrade_with_bad_database_url_does_not_echo_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "mysql://capsule:hunter2@db.invalid/capsule")

    with pytest.raises(ConfigError) as caught:
        command.upgrade(alembic_config(), "head")

    assert "hunter2" not in str(caught.value)
    assert "db.invalid" not in str(caught.value)
