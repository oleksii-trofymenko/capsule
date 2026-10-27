"""Responses match contracts/openapi.yaml, and the app serves exactly the operations it declares.

Readiness here uses fake probes; tests/integration repeats the checks against real services.
"""

from typing import Any

import pytest
from jsonschema import Draft202012Validator

from core.health import get_probes
from main import create_app
from tests.support import (
    assert_matches_contract,
    client_for,
    contract,
    dummy_settings,
    schema_validator,
)

HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


async def _ok() -> None:
    return None


async def _refused() -> None:
    raise ConnectionRefusedError


def test_contract_is_openapi_31_with_valid_schemas() -> None:
    spec = contract()

    assert spec["openapi"].startswith("3.1.")
    for schema in spec["components"]["schemas"].values():
        Draft202012Validator.check_schema(schema)


def test_app_serves_exactly_the_declared_operations() -> None:
    declared = {
        (path, method.upper())
        for path, item in contract()["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }
    # FastAPI's own schema is built in memory only; the app does not serve it (openapi_url=None).
    served = {
        (path, method.upper())
        for path, item in create_app(dummy_settings()).openapi()["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }

    assert served == declared


def test_app_declares_the_contract_status_codes() -> None:
    # FastAPI does not declare the 500 that the middleware returns, so it is left out.
    def statuses(paths: dict[str, Any]) -> dict[tuple[str, str], set[str]]:
        return {
            (path, method): set(operation["responses"]) - {"500"}
            for path, item in paths.items()
            for method, operation in item.items()
            if method in HTTP_METHODS
        }

    app_paths = create_app(dummy_settings()).openapi()["paths"]

    assert statuses(app_paths) == statuses(contract()["paths"])


@pytest.mark.anyio
async def test_health_matches_contract() -> None:
    async with client_for(create_app(dummy_settings())) as client:
        response = await client.get("/v1/health")

    assert_matches_contract(response, "/v1/health")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("postgres", "redis", "status"),
    [(_ok, _ok, 200), (_refused, _ok, 503), (_refused, _refused, 503)],
)
async def test_ready_matches_contract(postgres: object, redis: object, status: int) -> None:
    app = create_app(dummy_settings())
    app.dependency_overrides[get_probes] = lambda: {"postgres": postgres, "redis": redis}
    async with client_for(app) as client:
        response = await client.get("/v1/ready")

    assert response.status_code == status
    assert_matches_contract(response, "/v1/ready")


@pytest.mark.anyio
async def test_unknown_path_matches_problem_schema() -> None:
    async with client_for(create_app(dummy_settings())) as client:
        response = await client.get("/v1/nope")

    assert response.headers["content-type"] == "application/problem+json"
    schema_validator({"$ref": "#/components/schemas/Problem"}).validate(response.json())


def test_contract_token_schemas_hold_the_adr_014_shape() -> None:
    pair = {
        "access_token": "a.b.c",
        "token_type": "Bearer",
        "expires_in": 600,
        "refresh_token": "r",
    }
    tokens = schema_validator({"$ref": "#/components/schemas/TokenPair"})
    session = schema_validator({"$ref": "#/components/schemas/GuestSession"})
    sign_in = schema_validator({"$ref": "#/components/schemas/GuestSignIn"})

    assert tokens.is_valid(pair)
    assert not tokens.is_valid(pair | {"expires_in": 3600})
    assert not tokens.is_valid(pair | {"token_type": "bearer"})
    assert not tokens.is_valid(pair | {"guest_credential": "g"})
    assert session.is_valid(pair | {"guest_credential": "g"})
    assert not session.is_valid(pair)
    # No pattern: a malformed credential reaches the server and gets 401, not 422.
    assert sign_in.is_valid({"guest_credential": "not base64 ?!"})
    assert not sign_in.is_valid({"guest_credential": "x" * 257})
    assert not sign_in.is_valid({})


def test_contract_guest_endpoint_declares_no_store_and_bearer_401() -> None:
    operation = contract()["paths"]["/v1/auth/guest"]["post"]
    unauthorized = contract()["components"]["responses"]["Unauthorized"]

    for status in ("200", "201"):
        assert "Cache-Control" in operation["responses"][status]["headers"]
    assert operation["responses"]["401"] == {"$ref": "#/components/responses/Unauthorized"}
    assert unauthorized["headers"]["WWW-Authenticate"]["schema"] == {"const": "Bearer"}
    assert "bearerAuth" in contract()["components"]["securitySchemes"]


def test_contract_rejects_a_ready_problem_without_failing() -> None:
    validator = schema_validator({"$ref": "#/components/schemas/ReadyProblem"})
    body = {"type": "about:blank", "title": "Service Unavailable", "status": 503}

    assert not validator.is_valid(body)
    assert not validator.is_valid(body | {"failing": []})
    assert not validator.is_valid(body | {"failing": ["mysql"]})
    assert validator.is_valid(body | {"failing": ["redis"]})
