"""Alembic environment (ADR-007): online migrations only, sync psycopg 3.

DATABASE_URL comes through core/config.py and is never echoed. Alembic runs as its own process
(the Compose `migrate` service or a developer shell), so a sync engine is fine here.
"""

import os

from alembic import context
from sqlalchemy import create_engine, pool

from core.config import database_url_from_env
from migrations.errors import sanitised_exit

# No ORM models yet. When tables arrive, point this at their MetaData for autogenerate.
target_metadata = None

if context.is_offline_mode():
    raise SystemExit("Offline (--sql) migrations are not supported; run against a database.")

engine = create_engine(
    database_url_from_env(os.environ),
    poolclass=pool.NullPool,
    hide_parameters=True,  # bound values never appear in errors or logs
)
try:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
except Exception as exc:
    # No chained exception: its text would reach the `migrate` container log.
    raise sanitised_exit(exc) from None
finally:
    engine.dispose()
