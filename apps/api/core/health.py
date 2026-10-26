"""GET /v1/health (liveness) and GET /v1/ready (Postgres and Redis), per contracts/openapi.yaml.

/v1/ready answers within the probe budget even when a dependency hangs. A probe that overruns is
cancelled but not awaited: drivers may block for seconds while cleaning up a hung connection
(psycopg waits up to 10 s for a query cancel), so the task finishes in the background while
`ProbeTasks` holds it. While it is still running, the next check reports that dependency as
failing at once instead of starting another probe, so hung connections never pile up.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from functools import partial
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core import db, redis_client
from core.config import Settings
from core.errors import Problem, problem_response, title_for

Dependency = Literal["postgres", "redis"]
Probe = Callable[[], Coroutine[Any, Any, None]]

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


class ProbeTasks:
    """Probes that overran their budget and are finishing their cleanup in the background."""

    def __init__(self) -> None:
        self._tasks: dict[Dependency, asyncio.Task[None]] = {}

    def busy(self, name: Dependency) -> bool:
        task = self._tasks.get(name)
        return task is not None and not task.done()

    def keep(self, name: Dependency, task: asyncio.Task[None]) -> None:
        task.cancel()
        self._tasks[name] = task
        task.add_done_callback(partial(_log_cleanup, name))

    async def drain(self, timeout_s: float) -> None:
        """Give running cleanups a bounded chance to finish (used at shutdown)."""
        pending = [task for task in self._tasks.values() if not task.done()]
        if pending:
            await asyncio.wait(pending, timeout=timeout_s)


def _log_cleanup(name: Dependency, task: asyncio.Task[None]) -> None:
    error = None if task.cancelled() else task.exception()
    logger.debug(
        "readiness probe cleanup finished",
        extra={"check": name, "error": type(error).__name__ if error else None},
    )


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_probe_tasks(request: Request) -> ProbeTasks:
    tasks: ProbeTasks = request.app.state.probe_tasks
    return tasks


def get_probes(request: Request) -> dict[Dependency, Probe]:
    state = request.app.state
    return {
        "postgres": partial(db.ping, state.engine),
        "redis": partial(redis_client.ping, state.redis),
    }


def _not_ready(name: Dependency, error: str) -> Dependency:
    # The exception type is enough to debug; its text may carry hosts or credentials.
    logger.warning("readiness check failed", extra={"check": name, "error": error})
    return name


async def run_probes(
    probes: dict[Dependency, Probe], background: ProbeTasks, timeout_s: float
) -> list[Dependency]:
    """Run probes in parallel; return the failing ones within `timeout_s`, in probe order."""
    failing: dict[Dependency, str] = {}
    tasks: dict[Dependency, asyncio.Task[None]] = {}
    for name, probe in probes.items():
        if background.busy(name):
            failing[name] = "PreviousProbeStillRunning"
        else:
            tasks[name] = asyncio.create_task(probe(), name=f"ready-probe-{name}")

    try:
        if tasks:
            await asyncio.wait(tasks.values(), timeout=timeout_s)
    finally:
        # On timeout, or if this request is cancelled, never await a probe's cleanup here.
        for name, task in tasks.items():
            if not task.done():
                background.keep(name, task)
                failing[name] = "TimeoutError"

    for name, task in tasks.items():
        if name not in failing and (error := task.exception()) is not None:
            failing[name] = type(error).__name__

    return [_not_ready(name, failing[name]) for name in probes if name in failing]


@router.get("/health", response_model=Health)
async def health() -> Health:
    return Health()


@router.get("/ready", response_model=Ready, responses={503: {"model": ReadyProblem}})
async def ready(
    settings: Annotated[Settings, Depends(get_settings)],
    probes: Annotated[dict[Dependency, Probe], Depends(get_probes)],
    background: Annotated[ProbeTasks, Depends(get_probe_tasks)],
) -> Ready | JSONResponse:
    failing = await run_probes(probes, background, settings.ready_probe_timeout_s)
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
