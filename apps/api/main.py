"""Application factory. Served by an ASGI server from E0-07: `create_app` with `--factory`."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from core import health
from core.config import Settings
from core.db import create_engine
from core.errors import install_problem_handlers
from core.logging import configure_logging
from core.middleware import RequestContextMiddleware
from core.redis_client import create_redis
from core.signing_keys import load_signing_keys


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env(os.environ, signing_keys=load_signing_keys())
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = create_engine(settings)
        app.state.redis = create_redis(settings)
        try:
            yield
        finally:
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
    install_problem_handlers(app)
    app.add_middleware(RequestContextMiddleware)
    app.include_router(health.router)
    return app
