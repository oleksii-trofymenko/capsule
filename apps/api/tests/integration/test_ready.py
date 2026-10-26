"""GET /v1/ready against real Postgres and Redis (ADR-016): CI service containers or `make test`.

"Down" is simulated per dependency by pointing its URL at a closed local port while the other
dependency stays real.
"""

import asyncio
import os
import time
from urllib.parse import urlsplit, urlunsplit

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy.engine import make_url

from core.config import ConfigError, Settings
from main import create_app
from tests.integration.tcp_proxy import StallingProxy
from tests.support import assert_matches_contract, client_for

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

CLOSED_POSTGRES = "postgresql+psycopg://capsule:unused@127.0.0.1:1/capsule"
CLOSED_REDIS = "redis://127.0.0.1:1/0"
# Windows retries refused loopback connections for ~2 s; a short timeout keeps "down" fast.
DOWN_TIMEOUT_S = 0.5


@pytest.fixture
def settings() -> Settings:
    try:
        settings = Settings.from_env(os.environ)
    except ConfigError as exc:
        pytest.fail(f"Integration tests need DATABASE_URL and REDIS_URL ({exc}). Run `make test`.")
    # Guard against a shell that points at a real database: test databases end in _test.
    database = make_url(settings.database_url.get_secret_value()).database or ""
    if not database.endswith("_test"):
        pytest.fail("DATABASE_URL must name a database ending in _test for integration tests.")
    return settings


async def _get_ready(settings: Settings) -> httpx.Response:
    async with client_for(create_app(settings), lifespan=True) as client:
        return await client.get("/v1/ready")


async def test_ready_when_postgres_and_redis_are_up(settings: Settings) -> None:
    response = await _get_ready(settings)

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok", "checks": {"postgres": "ok", "redis": "ok"}}
    assert_matches_contract(response, "/v1/ready")


@pytest.mark.parametrize(
    ("overrides", "failing"),
    [
        ({"database_url": SecretStr(CLOSED_POSTGRES)}, ["postgres"]),
        ({"redis_url": SecretStr(CLOSED_REDIS)}, ["redis"]),
        (
            {"database_url": SecretStr(CLOSED_POSTGRES), "redis_url": SecretStr(CLOSED_REDIS)},
            ["postgres", "redis"],
        ),
    ],
    ids=["postgres-down", "redis-down", "both-down"],
)
async def test_not_ready_names_what_is_down(
    settings: Settings, overrides: dict[str, object], failing: list[str]
) -> None:
    down = settings.model_copy(update=overrides | {"ready_probe_timeout_s": DOWN_TIMEOUT_S})

    response = await _get_ready(down)

    assert response.status_code == 503
    assert response.json()["failing"] == failing
    assert "127.0.0.1" not in response.text  # connection details stay in the server
    assert_matches_contract(response, "/v1/ready")


async def test_repeated_checks_reuse_the_pool_and_release_connections(settings: Settings) -> None:
    app = create_app(settings)
    async with client_for(app, lifespan=True) as client:
        statuses = [(await client.get("/v1/ready")).status_code for _ in range(5)]
        pool = app.state.engine.pool

        assert statuses == [200] * 5
        assert pool.checkedout() == 0
        assert pool.checkedin() == 1


# A server that stops answering: /v1/ready must still answer within the budget (+ margin),
# before a connection exists and on an established pooled one, and recover without leaks.
STALL_BUDGET_S = 0.3
STALL_MARGIN_S = 0.25


def _via_proxy(url: str, port: int) -> str:
    parts = urlsplit(url)
    userinfo = parts.netloc.rpartition("@")[0]
    netloc = f"{userinfo}@127.0.0.1:{port}" if userinfo else f"127.0.0.1:{port}"
    return urlunsplit(parts._replace(netloc=netloc))


@pytest.mark.parametrize("when", ["before-connect", "established"])
@pytest.mark.parametrize("dependency", ["postgres", "redis"])
async def test_ready_answers_within_budget_when_a_dependency_stops_answering(
    settings: Settings, dependency: str, when: str
) -> None:
    field = "database_url" if dependency == "postgres" else "redis_url"
    url = getattr(settings, field).get_secret_value()
    upstream = urlsplit(url)
    default_port = 5432 if dependency == "postgres" else 6379
    proxy = StallingProxy(upstream.hostname or "127.0.0.1", upstream.port or default_port)

    async with proxy.running():
        app = create_app(
            settings.model_copy(
                update={
                    field: SecretStr(_via_proxy(url, proxy.port)),
                    "ready_probe_timeout_s": STALL_BUDGET_S,
                }
            )
        )
        async with client_for(app, lifespan=True) as client:
            if when == "established":
                assert (await client.get("/v1/ready")).status_code == 200
            proxy.stall()

            # The second call meets the first probe still cleaning up (or a fresh stall).
            for _ in range(2):
                started = time.perf_counter()
                response = await client.get("/v1/ready")
                elapsed = time.perf_counter() - started

                assert response.status_code == 503
                assert response.json()["failing"] == [dependency]
                assert elapsed <= STALL_BUDGET_S + STALL_MARGIN_S

            proxy.resume()
            await app.state.probe_tasks.drain(5.0)

            assert (await client.get("/v1/ready")).status_code == 200
            assert app.state.engine.pool.checkedout() == 0
            assert not [t for t in asyncio.all_tasks() if t.get_name().startswith("ready-probe")]
