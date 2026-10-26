"""GET /v1/ready against real Postgres and Redis (ADR-016): CI service containers or `make test`.

"Down" is simulated per dependency by pointing its URL at a closed local port while the other
dependency stays real.
"""

import os

import httpx
import pytest
from pydantic import SecretStr

from core.config import ConfigError, Settings
from main import create_app
from tests.support import assert_matches_contract, client_for

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

CLOSED_POSTGRES = "postgresql+psycopg://capsule:unused@127.0.0.1:1/capsule"
CLOSED_REDIS = "redis://127.0.0.1:1/0"
# Windows retries refused loopback connections for ~2 s; a short timeout keeps "down" fast.
DOWN_TIMEOUT_S = 0.5


@pytest.fixture
def settings() -> Settings:
    try:
        return Settings.from_env(os.environ)
    except ConfigError as exc:
        pytest.fail(f"Integration tests need DATABASE_URL and REDIS_URL ({exc}). Run `make test`.")


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
    down = settings.model_copy(update=overrides | {"ready_check_timeout_s": DOWN_TIMEOUT_S})

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
