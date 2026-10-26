"""GET /v1/health (liveness) and GET /v1/ready (Postgres and Redis), per contracts/openapi.yaml.

/v1/ready answers within the probe budget even when a dependency hangs:

- Single flight: at most one probe task per dependency exists at a time. Concurrent requests
  wait on the same task, each within its own budget; `ProbeTasks` holds it until it ends.
- A probe that overruns is cancelled but not awaited: drivers may block for seconds while
  cleaning up a hung connection (psycopg waits up to 10 s for a query cancel). Until that
  cleanup ends, requests report the dependency as failing at once instead of probing again,
  so hung connections and tasks never pile up.
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
    """The one live probe task per dependency, held from creation until it ends."""

    def __init__(self) -> None:
        self._tasks: dict[Dependency, asyncio.Task[None]] = {}

    def start(self, name: Dependency, probe: Probe) -> asyncio.Task[None] | None:
        """Join the running probe, or start one. None while an overrun probe is cleaning up."""
        task = self._tasks.get(name)
        if task is not None and not task.done():
            return None if task.cancelling() else task
        task = asyncio.create_task(probe(), name=f"ready-probe-{name}")
        task.add_done_callback(partial(_finished, name))
        self._tasks[name] = task
        return task

    def live(self) -> int:
        return sum(not task.done() for task in self._tasks.values())

    async def drain(self, timeout_s: float) -> None:
        """Give running probes a bounded chance to finish (used at shutdown)."""
        pending = [task for task in self._tasks.values() if not task.done()]
        if pending:
            await asyncio.wait(pending, timeout=timeout_s)


def _finished(name: Dependency, task: asyncio.Task[None]) -> None:
    # Always retrieve the outcome, so no "Task exception was never retrieved" at any point.
    error = None if task.cancelled() else task.exception()
    if not task.cancelling():
        return  # finished within some request's budget; that request reported it
    if error is None:
        logger.debug("readiness probe cleanup finished", extra={"check": name})
    else:
        logger.warning(
            "readiness probe cleanup failed",
            extra={"check": name, "error": type(error).__name__},
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
        task = background.start(name, probe)
        if task is None:
            failing[name] = "PreviousProbeStillRunning"
        else:
            tasks[name] = task

    # asyncio.wait never cancels the tasks it waits on, so a cancelled request leaves the shared
    # probes running for other requests; ProbeTasks keeps them referenced.
    if tasks:
        await asyncio.wait(tasks.values(), timeout=timeout_s)

    for name, task in tasks.items():
        if not task.done():
            task.cancel()  # stop the hung call; its cleanup is not awaited here
            failing[name] = "TimeoutError"
        elif task.cancelled():
            failing[name] = "CancelledError"
        elif (error := task.exception()) is not None:
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
