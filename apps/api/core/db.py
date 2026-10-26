"""Postgres access through SQLAlchemy 2 async with the psycopg 3 driver (ADR-007)."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        hide_parameters=True,  # bound values never appear in SQLAlchemy errors or logs
        connect_args={"connect_timeout": settings.database_connect_timeout_s},
    )


async def ping(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
