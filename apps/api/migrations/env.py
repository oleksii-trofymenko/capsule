"""Alembic environment (ADR-007): online migrations only, sync psycopg 3.

DATABASE_URL comes through core/config.py and is never echoed. Alembic runs as its own process
(the Compose `migrate` service or a developer shell), so a sync engine is fine here.
"""

import os

from alembic import context
from sqlalchemy import Engine, create_engine, pool

from core.config import database_url_from_env
from migrations.errors import sanitised_exit

# No ORM models yet. When tables arrive, point this at their MetaData for autogenerate.
target_metadata = None

# A migration waiting on a lock holds up every api query queued behind it (E1-27): fail fast and
# roll back instead. A migration that needs longer runs `SET LOCAL lock_timeout = '30s'` itself.
LOCK_TIMEOUT = "5s"

if context.is_offline_mode():
    raise SystemExit("Offline (--sql) migrations are not supported; run against a database.")

engine: Engine | None = None
try:
    # Inside the try: a malformed URL must exit with the sanitised line, not a traceback.
    engine = create_engine(
        database_url_from_env(os.environ),
        poolclass=pool.NullPool,
        hide_parameters=True,  # bound values never appear in errors or logs
        # Session-level, so it also covers autocommit_block() steps. Overrides any `options`
        # query parameter in DATABASE_URL.
        connect_args={"options": f"-c lock_timeout={LOCK_TIMEOUT}"},
    )
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
except Exception as exc:
    # No chained exception: its text would reach the `migrate` container log.
    raise sanitised_exit(exc) from None
finally:
    if engine is not None:
        engine.dispose()
