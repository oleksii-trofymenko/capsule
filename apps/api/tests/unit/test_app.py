"""The app with fake readiness probes: no network (integration tests use real services)."""

import asyncio
import json
import time

import pytest
from fastapi import FastAPI

from core.health import Dependency, Probe, get_probes
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
    app = create_app(dummy_settings(ready_check_timeout_s=timeout_s))
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
