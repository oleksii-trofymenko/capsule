from collections.abc import Callable
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from core.config import ConfigError, Settings, database_url_from_env, normalise_database_url
from tests.support import TEST_SIGNING_KEYS

REQUIRED = {
    "DATABASE_URL": "postgresql://capsule:dummy@localhost:5432/capsule",
    "REDIS_URL": "redis://localhost:6379/0",
}


def _from_env(environ: dict[str, str]) -> Settings:
    return Settings.from_env(environ, signing_keys=TEST_SIGNING_KEYS)


def test_from_env_reads_variables_and_applies_defaults() -> None:
    settings = _from_env(REQUIRED)

    assert settings.database_url.get_secret_value() == (
        "postgresql+psycopg://capsule:dummy@localhost:5432/capsule"
    )
    assert settings.redis_url.get_secret_value() == "redis://localhost:6379/0"
    assert settings.log_level == "INFO"
    assert settings.ready_probe_timeout_s == 1.0
    assert settings.database_connect_timeout_s == 5
    assert settings.redis_socket_timeout_s == 5.0
    assert settings.guest_retention_days == 30
    assert settings.deletion_ledger_dir is None  # no default path in code (ADR-022)
    assert settings.signing_keys == TEST_SIGNING_KEYS


def test_from_env_reads_optional_variables() -> None:
    settings = _from_env(
        REQUIRED
        | {
            "LOG_LEVEL": "DEBUG",
            "READY_PROBE_TIMEOUT_S": "2.5",
            "DATABASE_CONNECT_TIMEOUT_S": "3",
            "REDIS_SOCKET_TIMEOUT_S": "0.75",
            "GUEST_RETENTION_DAYS": "7",
        }
    )

    assert settings.log_level == "DEBUG"
    assert settings.ready_probe_timeout_s == 2.5
    assert settings.database_connect_timeout_s == 3
    assert settings.redis_socket_timeout_s == 0.75
    assert settings.guest_retention_days == 7


def test_deletion_ledger_dir_is_read_and_empty_means_unset(tmp_path: Path) -> None:
    read = _from_env(REQUIRED | {"DELETION_LEDGER_DIR": str(tmp_path)}).deletion_ledger_dir

    assert read == tmp_path
    assert _from_env(REQUIRED | {"DELETION_LEDGER_DIR": ""}).deletion_ledger_dir is None


@pytest.mark.parametrize("value", ["ledger", "./ledger", "../srv/ledger"])
def test_relative_deletion_ledger_dir_is_rejected(value: str) -> None:
    # It would resolve inside the container, not on the mounted disk (ADR-022).
    with pytest.raises(ConfigError, match="DELETION_LEDGER_DIR: Value error, must be an absolute"):
        _from_env(REQUIRED | {"DELETION_LEDGER_DIR": value})


def test_missing_variable_is_named() -> None:
    with pytest.raises(ConfigError, match="REDIS_URL"):
        _from_env({"DATABASE_URL": REQUIRED["DATABASE_URL"]})


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("DATABASE_URL", "mysql://capsule:hunter2@localhost/capsule"),
        ("DATABASE_URL", "postgresql+asyncpg://capsule:hunter2@localhost/capsule"),
        ("DATABASE_URL", "postgresql://capsule:hunter2@/capsule"),
        ("REDIS_URL", "http://capsule:hunter2@localhost:6379"),
    ],
)
def test_invalid_url_is_rejected_without_echoing_it(name: str, value: str) -> None:
    with pytest.raises(ConfigError) as caught:
        _from_env(REQUIRED | {name: value})

    assert name in str(caught.value)
    assert "hunter2" not in str(caught.value)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("READY_PROBE_TIMEOUT_S", "0"),
        ("READY_PROBE_TIMEOUT_S", "11"),
        ("READY_PROBE_TIMEOUT_S", "soon"),
        ("DATABASE_CONNECT_TIMEOUT_S", "0"),
        ("DATABASE_CONNECT_TIMEOUT_S", "1.5"),  # libpq takes whole seconds
        ("REDIS_SOCKET_TIMEOUT_S", "-1"),
        ("REDIS_SOCKET_TIMEOUT_S", "61"),
        ("GUEST_RETENTION_DAYS", "0"),
        ("GUEST_RETENTION_DAYS", "31"),  # ADR-022 upper bound
    ],
)
def test_timeouts_must_be_sane_numbers(name: str, value: str) -> None:
    with pytest.raises(ConfigError, match=name):
        _from_env(REQUIRED | {name: value})


def test_database_url_from_env_normalises_the_driver() -> None:
    assert database_url_from_env(REQUIRED) == (
        "postgresql+psycopg://capsule:dummy@localhost:5432/capsule"
    )


@pytest.mark.parametrize(
    "environ",
    [
        {},
        {"DATABASE_URL": "mysql://capsule:hunter2@localhost/capsule"},
        {"DATABASE_URL": "postgresql://capsule:hunter2@/capsule"},
        {"DATABASE_URL": "hunter2"},
    ],
    ids=["missing", "wrong-scheme", "no-host", "not-a-url"],
)
def test_database_url_from_env_rejects_without_echoing(environ: dict[str, str]) -> None:
    with pytest.raises(ConfigError, match="DATABASE_URL") as caught:
        database_url_from_env(environ)

    message = str(caught.value)
    assert "hunter2" not in message
    assert "localhost" not in message
    assert "capsule" not in message


@pytest.mark.parametrize(
    "parse",
    [
        lambda url: normalise_database_url(url),
        lambda url: database_url_from_env({"DATABASE_URL": url}),
        lambda url: _from_env(REQUIRED | {"DATABASE_URL": url}),
    ],
    ids=["normalise", "from-env-url-only", "settings"],
)
def test_unparseable_host_is_rejected_without_echoing(parse: Callable[[str], object]) -> None:
    # urlsplit's own ValueError quotes the bracketed host.
    with pytest.raises(ConfigError, match="DATABASE_URL") as caught:
        parse("postgresql://u:pw@[secrethost]/db")

    assert "secrethost" not in str(caught.value)
    assert "pw" not in str(caught.value)
    assert caught.value.__suppress_context__


def test_secrets_are_hidden_in_repr() -> None:
    settings = _from_env(REQUIRED)

    assert "dummy" not in repr(settings)
    assert "dummy" not in str(settings.model_dump())
    key = TEST_SIGNING_KEYS[0].key.get_secret_value()
    assert key.hex() not in repr(settings)
    assert repr(key) not in repr(settings)


_part = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=20)


@given(
    scheme=st.sampled_from(["postgres", "postgresql", "POSTGRESQL", "postgresql+psycopg"]),
    user=_part,
    password=_part,
    host=_part,
    port=st.integers(min_value=1, max_value=65535),
    db=_part,
)
def test_normalise_database_url_sets_psycopg_and_is_idempotent(
    scheme: str, user: str, password: str, host: str, port: int, db: str
) -> None:
    rest = f"{user}:{password}@{host}:{port}/{db}"

    once = normalise_database_url(f"{scheme}://{rest}")

    assert once == f"postgresql+psycopg://{rest}"
    assert normalise_database_url(once) == once
