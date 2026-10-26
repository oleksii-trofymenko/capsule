"""GET /v1/health (liveness) and GET /v1/ready (Postgres and Redis), per contracts/openapi.yaml."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core import db, redis_client
from core.config import Settings
from core.errors import Problem, problem_response, title_for

Dependency = Literal["postgres", "redis"]
Probe = Callable[[], Awaitable[None]]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["ops"])


class Health(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyChecks(BaseModel):
    postgres: Literal["ok"] = "ok"
    redis: Literal["ok"] = "ok"


class Ready(BaseModel):
    status: Literal["ok"] = "ok"
    checks: ReadyChecks = ReadyChecks()


class ReadyProblem(Problem):
    failing: list[Dependency]


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_probes(request: Request) -> dict[Dependency, Probe]:
    state = request.app.state
    return {
        "postgres": partial(db.ping, state.engine),
        "redis": partial(redis_client.ping, state.redis),
    }


async def _check(name: Dependency, probe: Probe, timeout_s: float) -> Dependency | None:
    try:
        async with asyncio.timeout(timeout_s):
            await probe()
    except Exception as exc:  # any failure means "not ready"; the type is enough to debug
        logger.warning("readiness check failed", extra={"check": name, "error": type(exc).__name__})
        return name
    return None


@router.get("/health", response_model=Health)
async def health() -> Health:
    return Health()


@router.get("/ready", response_model=Ready, responses={503: {"model": ReadyProblem}})
async def ready(
    settings: Annotated[Settings, Depends(get_settings)],
    probes: Annotated[dict[Dependency, Probe], Depends(get_probes)],
) -> Ready | JSONResponse:
    results = await asyncio.gather(
        *(_check(name, probe, settings.ready_check_timeout_s) for name, probe in probes.items())
    )
    failing = [name for name in results if name is not None]
    if failing:
        return problem_response(
            ReadyProblem(
                title=title_for(503),
                status=503,
                detail="Not ready: " + ", ".join(failing),
                failing=failing,
            )
        )
    return Ready()
