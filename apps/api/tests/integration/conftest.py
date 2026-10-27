import os

import pytest
from alembic import command
from sqlalchemy.engine import make_url

from core.config import ConfigError, database_url_from_env
from tests.support import alembic_config


def checked_database_url() -> str:
    """DATABASE_URL, refused unless it names a database ending in _test."""
    try:
        url = database_url_from_env(os.environ)
    except ConfigError as exc:
        pytest.fail(f"Integration tests need DATABASE_URL ({exc}). Run `make test`.")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("DATABASE_URL must name a database ending in _test for integration tests.")
    return url


@pytest.fixture(scope="session", autouse=True)
def _migrated_test_database() -> None:
    """Every integration test runs against the schema at head (env.py reads DATABASE_URL)."""
    checked_database_url()
    command.upgrade(alembic_config(), "head")
