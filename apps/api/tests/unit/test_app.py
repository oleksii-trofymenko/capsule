"""The app with fake readiness probes: no network (integration tests use real services)."""

import asyncio
import gc
import json
import logging
import time

import pytest
from fastapi import FastAPI, HTTPException

from core.health import Dependency, Probe, ProbeTasks, get_probes
from main import create_app
from tests.support import client_for, dummy_settings

pytestmark = pytest.mark.anyio

PROBLEM = "application/problem+json"


async def _ok() -> None:
    return None


async def _refused() -> None:
    raise ConnectionRefusedError("connection refused by db.invalid:5432")


async def _hangs() -> None:
    await asyncio.sleep(10)


def _app_with(probes: dict[Dependency, Probe], timeout_s: float = 1.0) -> FastAPI:
    app = create_app(dummy_settings(ready_probe_timeout_s=timeout_s))
    app.dependency_overrides[get_probes] = lambda: probes
    return app


async def test_health_is_ok_and_gets_a_request_id() -> None:
    async with client_for(create_app(dummy_settings())) as client:
        response = await client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert len(response.headers["X-Request-ID"]) == 32


async def test_valid_client_request_id_is_kept() -> None:
    async with client_for(create_app(dummy_settings())) as client:
        response = await client.get("/v1/health", headers={"X-Request-ID": "abc-123"})

    assert response.headers["X-Request-ID"] == "abc-123"


@pytest.mark.parametrize("bad", ["a" * 65, "has space", "semi;colon", ""])
async def test_malformed_client_request_id_is_replaced(bad: str) -> None:
    async with client_for(create_app(dummy_settings())) as client:
        response = await client.get("/v1/health", headers={"X-Request-ID": bad})

    assert response.headers["X-Request-ID"] != bad
    assert len(response.headers["X-Request-ID"]) == 32


async def test_ready_when_every_probe_answers() -> None:
    async with client_for(_app_with({"postgres": _ok, "redis": _ok})) as client:
        response = await client.get("/v1/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"postgres": "ok", "redis": "ok"}}


async def test_not_ready_names_the_failing_dependency() -> None:
    async with client_for(_app_with({"postgres": _ok, "redis": _refused})) as client:
        response = await client.get("/v1/ready", headers={"X-Request-ID": "rid-503"})

    assert response.status_code == 503
    assert response.headers["content-type"] == PROBLEM
    body = response.json()
    assert body["failing"] == ["redis"]
    assert body["detail"] == "Not ready: redis"
    assert body["request_id"] == "rid-503"
    assert "db.invalid" not in response.text  # the exception text is not returned


async def test_hanging_probe_times_out_within_budget() -> None:
    app = _app_with({"postgres": _hangs, "redis": _hangs}, timeout_s=0.05)
    async with client_for(app) as client:
        started = time.perf_counter()
        response = await client.get("/v1/ready")
        elapsed = time.perf_counter() - started

    assert response.status_code == 503
    assert response.json()["failing"] == ["postgres", "redis"]
    assert elapsed < 1.0  # both probes run in parallel and stop at the timeout


async def test_unknown_path_is_a_problem() -> None:
    async with client_for(create_app(dummy_settings())) as client:
        response = await client.get("/v1/nope")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM
    body = response.json()
    assert body == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "request_id": response.headers["X-Request-ID"],
    }


async def test_wrong_method_is_a_problem_with_allow_header() -> None:
    async with client_for(create_app(dummy_settings())) as client:
        response = await client.post("/v1/health")

    assert response.status_code == 405
    assert response.headers["content-type"] == PROBLEM
    assert response.headers["allow"] == "GET"


async def test_non_string_http_detail_is_dropped_not_a_500() -> None:
    app = create_app(dummy_settings())

    @app.get("/test/conflict")
    async def conflict() -> None:
        raise HTTPException(status_code=409, detail={"internal": "row-id-7"})

    async with client_for(app) as client:
        response = await client.get("/test/conflict")

    assert response.status_code == 409
    assert response.headers["content-type"] == PROBLEM
    assert "detail" not in response.json()
    assert "row-id-7" not in response.text


async def test_validation_error_does_not_echo_input() -> None:
    app = create_app(dummy_settings())

    @app.get("/test/items/{item_id}")
    async def item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    async with client_for(app) as client:
        response = await client.get("/test/items/secret-value-42")

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM
    body = response.json()
    assert body["errors"][0]["loc"] == ["path", "item_id"]
    assert set(body["errors"][0]) == {"loc", "msg", "type"}
    assert "secret-value-42" not in response.text


async def test_unhandled_error_is_a_generic_problem_and_is_logged(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = create_app(dummy_settings())

    @app.get("/test/boom")
    async def boom() -> None:
        raise RuntimeError("internal-marker")

    async with client_for(app) as client:
        response = await client.get("/test/boom", headers={"X-Request-ID": "rid-500"})

    assert response.status_code == 500
    assert response.headers["content-type"] == PROBLEM
    assert response.headers["X-Request-ID"] == "rid-500"
    assert response.json() == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "request_id": "rid-500",
    }
    assert "internal-marker" not in response.text

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    error = next(line for line in lines if line["msg"] == "unhandled error")
    assert error["request_id"] == "rid-500"
    assert "internal-marker" in error["exc"]
    access = next(line for line in lines if line["msg"] == "request")
    assert access == access | {"path": "/test/boom", "status": 500, "request_id": "rid-500"}


async def test_probe_with_slow_cleanup_is_not_awaited_or_restarted() -> None:
    calls = 0

    async def slow_cleanup() -> None:
        nonlocal calls
        calls += 1
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(0.3)  # like psycopg cancelling a query on a hung connection
            raise

    app = _app_with({"postgres": slow_cleanup, "redis": _ok}, timeout_s=0.05)
    async with client_for(app) as client:
        started = time.perf_counter()
        first = await client.get("/v1/ready")
        second = await client.get("/v1/ready")
        elapsed = time.perf_counter() - started

        assert [first.status_code, second.status_code] == [503, 503]
        assert second.json()["failing"] == ["postgres"]
        assert elapsed < 0.25  # neither call waited for the 0.3 s cleanup
        assert calls == 1  # no second probe while the first is still cleaning up

        await app.state.probe_tasks.drain(1.0)
        third = await client.get("/v1/ready")

    assert third.status_code == 503
    assert calls == 2


async def test_concurrent_checks_share_one_probe_per_dependency() -> None:
    calls = 0

    async def slow_cleanup() -> None:
        nonlocal calls
        calls += 1
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(0.3)
            raise

    budget = 0.1
    app = _app_with({"postgres": slow_cleanup, "redis": _ok}, timeout_s=budget)
    async with client_for(app) as client:

        async def timed() -> tuple[int, list[str], float]:
            started = time.perf_counter()
            response = await client.get("/v1/ready")
            return response.status_code, response.json()["failing"], time.perf_counter() - started

        results = await asyncio.gather(*(timed() for _ in range(5)))
        live = [t for t in asyncio.all_tasks() if t.get_name().startswith("ready-probe-")]

        assert calls == 1
        assert all(status == 503 and failing == ["postgres"] for status, failing, _ in results)
        assert max(elapsed for *_, elapsed in results) <= budget + 0.25
        assert len(live) == 1  # the one postgres probe, still cleaning up
        assert app.state.probe_tasks.live() == 1  # and it is tracked

        await app.state.probe_tasks.drain(1.0)
        assert app.state.probe_tasks.live() == 0


async def test_probe_that_cancels_itself_reports_failing_not_500() -> None:
    async def cancels_itself() -> None:
        raise asyncio.CancelledError

    async with client_for(_app_with({"postgres": _ok, "redis": cancels_itself})) as client:
        response = await client.get("/v1/ready")

    assert response.status_code == 503
    assert response.json()["failing"] == ["redis"]


async def test_late_joiner_does_not_interrupt_cleanup() -> None:
    calls = 0
    cleanup_completed = False

    async def slow_cleanup() -> None:
        nonlocal calls, cleanup_completed
        calls += 1
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(0.3)  # a second cancel landing here would cut the cleanup short
            cleanup_completed = True
            raise

    app = _app_with({"postgres": slow_cleanup, "redis": _ok}, timeout_s=0.1)
    async with client_for(app) as client:
        first = asyncio.create_task(client.get("/v1/ready"))
        await asyncio.sleep(0.05)  # the second request joins the same probe, budget ends later
        second = await client.get("/v1/ready")
        assert (await first).status_code == second.status_code == 503

        await app.state.probe_tasks.drain(1.0)

    assert cleanup_completed
    assert calls == 1


async def test_probe_failure_is_retrieved_even_without_a_waiting_request(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR, logger="asyncio")
    tasks = ProbeTasks()
    tasks.start("postgres", _refused)  # nobody awaits it, as after a cancelled request
    await asyncio.sleep(0.01)
    del tasks
    gc.collect()

    assert "exception was never retrieved" not in caplog.text
