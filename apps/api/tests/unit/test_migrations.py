"""Alembic checks that need no database."""

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from migrations.errors import sanitised_exit

from core.config import ConfigError
from tests.support import alembic_config


def test_revision_history_has_a_single_head() -> None:
    # Two heads mean two branches added migrations in parallel: merge them before shipping.
    heads = ScriptDirectory.from_config(alembic_config()).get_heads()

    assert len(heads) == 1, f"expected one head, got {heads}"


def test_sanitised_exit_keeps_only_the_type_of_a_non_database_error() -> None:
    exit_ = sanitised_exit(KeyError("secret@example.invalid"))

    assert str(exit_) == "migration failed: KeyError"


def test_sanitised_exit_keeps_the_fixed_config_error_message() -> None:
    exit_ = sanitised_exit(ConfigError("Invalid settings: DATABASE_URL: host is not valid"))

    assert str(exit_) == "ConfigError: Invalid settings: DATABASE_URL: host is not valid"


def _upgrade_exit(monkeypatch: pytest.MonkeyPatch, url: str | None) -> SystemExit:
    """Run `upgrade head` with this DATABASE_URL and return the clean exit it must end in."""
    if url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(SystemExit) as caught:
        command.upgrade(alembic_config(), "head")
    # Nothing chained: no traceback of the original error reaches the `migrate` log.
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    return caught.value


def test_upgrade_without_database_url_fails_before_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exit_ = _upgrade_exit(monkeypatch, None)

    assert str(exit_) == "ConfigError: Invalid settings: DATABASE_URL: Field required"


def test_upgrade_with_bad_database_url_does_not_echo_it(monkeypatch: pytest.MonkeyPatch) -> None:
    exit_ = _upgrade_exit(monkeypatch, "mysql://capsule:hunter2@db.invalid/capsule")

    assert str(exit_) == (
        "ConfigError: Invalid settings: DATABASE_URL: "
        "must start with postgresql:// or postgresql+psycopg://"
    )


def test_upgrade_with_bracketed_host_exits_with_the_fixed_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # urlsplit's own message would quote the host.
    exit_ = _upgrade_exit(monkeypatch, "postgresql://capsule:hunter2@[db.invalid/capsule")

    assert str(exit_) == "ConfigError: Invalid settings: DATABASE_URL: host is not valid"


def test_upgrade_with_non_numeric_port_exits_without_any_url_part(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Passes config validation; create_engine rejects it with a message that quotes the port.
    exit_ = _upgrade_exit(monkeypatch, "postgresql://capsule:hunter2@db.invalid:p0rt/capsule")

    assert str(exit_) == "migration failed: ValueError"
