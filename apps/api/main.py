"""Application factory. Served by an ASGI server from E0-07: `create_app` with `--factory`."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from core import health
from core.config import ConfigError, Settings
from core.db import create_engine, create_sessionmaker
from core.errors import install_problem_handlers
from core.logging import configure_logging
from core.middleware import RequestContextMiddleware
from core.redis_client import create_redis
from core.signing_keys import load_signing_keys
from modules import auth


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env(os.environ, signing_keys=load_signing_keys())
    if not settings.signing_keys:
        raise ConfigError("Invalid settings: no JWT signing keys")
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = create_engine(settings)
        app.state.sessionmaker = create_sessionmaker(app.state.engine)
        app.state.redis = create_redis(settings)
        hash_executor = auth.create_hash_executor()
        app.state.password_hashing = auth.PasswordHashing(hash_executor)
        try:
            yield
        finally:
            # Queued hashes are dropped; a running one finishes in its thread, unawaited.
            hash_executor.shutdown(wait=False, cancel_futures=True)
            # Probes that overran /v1/ready may still be closing their connections. A psycopg
            # cleanup that outlasts this bounded wait can log "Task was destroyed but it is
            # pending" when the loop closes; that is bounded and acceptable at shutdown.
            await app.state.probe_tasks.drain(settings.ready_probe_timeout_s)
            try:
                await app.state.redis.aclose()
            finally:
                await app.state.engine.dispose()

    # The contract lives in contracts/openapi.yaml; the app does not publish a second one.
    app = FastAPI(
        title="Capsule API",
        version="0.1.0",
        lifespan=lifespan,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.probe_tasks = health.ProbeTasks()
    app.state.tokens = auth.TokenService(settings)
    install_problem_handlers(app)
    # Added first, so it runs inside the request context and sees the final status.
    app.add_middleware(auth.LastActivityMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.include_router(health.router)
    app.include_router(auth.router)
    return app
