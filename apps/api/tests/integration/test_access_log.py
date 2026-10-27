"""R4 (ADR-021): the access line under a real uvicorn server holds no client IP or query string."""

import asyncio
import json
import socket

import httpx
import pytest
import uvicorn

from core.logging import SERVER_ACCESS_LOGGER
from main import create_app
from tests.support import dummy_settings

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

PII = "someone@example.invalid"

ACCESS_FIELDS = ("method", "path", "status", "duration_ms")


@pytest.mark.usefixtures("uvicorn_logging")  # restores what uvicorn.Config's dictConfig changes
async def test_access_line_has_no_client_ip_or_query_under_real_uvicorn(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """R4: uvicorn with its access log switched on, as if `--no-access-log` were forgotten."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    config = uvicorn.Config(lambda: create_app(dummy_settings()), factory=True, lifespan="off")
    assert config.access_log
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        async with asyncio.timeout(5):
            while not server.started:  # noqa: ASYNC110 - uvicorn exposes only this flag
                await asyncio.sleep(0.01)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://127.0.0.1:{port}/v1/health?email={PII}",
                headers={"X-Forwarded-For": "203.0.113.7"},
            )
    finally:
        server.should_exit = True
        await task
        sock.close()

    assert response.status_code == 200
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert not [line for line in lines if line["logger"] == SERVER_ACCESS_LOGGER]
    access = [line for line in lines if line["msg"] == "request"]
    assert len(access) == 1
    assert set(access[0]) == {"ts", "level", "logger", "msg", "request_id", *ACCESS_FIELDS}
    assert access[0]["path"] == "/v1/health"
    raw = json.dumps(lines)
    assert PII not in raw
    assert "203.0.113.7" not in raw
    # uvicorn.error's startup line names the listening socket; no other line holds the IP.
    others = [line for line in lines if line["logger"] != "uvicorn.error"]
    assert "127.0.0.1" not in json.dumps(others)
