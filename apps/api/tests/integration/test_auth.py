"""Guest credential, current principal and last activity against real Postgres (E1-05)."""

import asyncio
import base64
import hashlib
import json
import os
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from core.config import Settings
from main import create_app
from modules.auth import CurrentPrincipal
from tests.integration.conftest import checked_database_url
from tests.support import A15, TEST_SIGNING_KEYS, assert_matches_contract, client_for
from tests.unit.test_tokens import forge, valid_claims

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

GUEST = "/v1/auth/guest"
ME = "/v1/test/me"
AUTH_TABLES = ("principals", "guest_credentials", "refresh_families", "refresh_tokens")


def make_app(**overrides: object) -> FastAPI:
    checked_database_url()
    settings = Settings.from_env(os.environ, signing_keys=TEST_SIGNING_KEYS)
    app = create_app(settings.model_copy(update=overrides))

    @app.get(ME)
    async def me(
        principal: CurrentPrincipal, fail: bool = False, crash: bool = False
    ) -> dict[str, str]:
        if fail:
            raise HTTPException(status_code=404)
        if crash:
            raise RuntimeError("unhandled")  # the middleware turns it into a 500
        return {"id": str(principal.id), "kind": principal.kind}

    return app


@pytest.fixture
async def app() -> AsyncIterator[FastAPI]:
    yield make_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with client_for(app, lifespan=True) as client:
        yield client


async def sql(app: FastAPI, query: str, **params: object) -> list[Any]:
    async with app.state.engine.begin() as conn:
        result = await conn.execute(text(query), params)
        return list(result.all()) if result.returns_rows else []


async def new_guest(client: httpx.AsyncClient) -> dict[str, Any]:
    response = await client.post(GUEST)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def principal_of(body: dict[str, Any]) -> uuid.UUID:
    claims = json.loads(base64.urlsafe_b64decode(body["access_token"].split(".")[1] + "=="))
    return uuid.UUID(claims["sub"])


def without_request_id(response: httpx.Response) -> dict[str, Any]:
    return {k: v for k, v in response.json().items() if k != "request_id"}


def assert_unauthorized(response: httpx.Response) -> None:
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert without_request_id(response) == {
        "type": "about:blank",
        "title": "Unauthorized",
        "status": 401,
    }


# --- POST /v1/auth/guest ---


async def test_new_guest_gets_201_rows_and_only_hashes(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    response = await client.post(GUEST)

    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"
    assert_matches_contract(response, GUEST, "post")
    body = response.json()
    principal = principal_of(body)
    assert await sql(app, "SELECT kind FROM principals WHERE id = :id", id=principal) == [
        ("guest",)
    ]
    credential = await sql(
        app, "SELECT credential_hash FROM guest_credentials WHERE principal_id = :id", id=principal
    )
    assert credential == [(hashlib.sha256(body["guest_credential"].encode()).digest(),)]
    tokens = await sql(
        app,
        "SELECT t.token_hash, t.state FROM refresh_tokens t JOIN refresh_families f"
        " ON f.id = t.family_id WHERE f.principal_id = :id",
        id=principal,
    )
    assert tokens == [(hashlib.sha256(body["refresh_token"].encode()).digest(), "current")]


async def test_existing_credential_gets_200_and_a_new_family(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    guest = await new_guest(client)

    response = await client.post(GUEST, json={"guest_credential": guest["guest_credential"]})

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert_matches_contract(response, GUEST, "post")
    assert principal_of(response.json()) == principal_of(guest)
    families = await sql(
        app,
        "SELECT count(*) FROM refresh_families WHERE principal_id = :id",
        id=principal_of(guest),
    )
    assert families == [(2,)]


async def test_expired_guest_gets_the_same_401_as_an_unknown_credential(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    guest = await new_guest(client)
    await sql(
        app,
        "UPDATE principals SET last_activity_at = now() - interval '31 days' WHERE id = :id",
        id=principal_of(guest),
    )

    expired = await client.post(GUEST, json={"guest_credential": guest["guest_credential"]})
    unknown = await client.post(GUEST, json={"guest_credential": "x" * 43})
    malformed = await client.post(GUEST, json={"guest_credential": "not base64 ?!"})

    for response in (expired, unknown, malformed):
        assert_unauthorized(response)
        assert_matches_contract(response, GUEST, "post")
    assert without_request_id(expired) == without_request_id(unknown)
    assert dict(expired.headers) | {"x-request-id": ""} == dict(unknown.headers) | {
        "x-request-id": ""
    }


@pytest.mark.parametrize(
    ("retention_days", "inactive_for", "status"),
    [
        (30, "30 days - 1 minute", 200),
        (30, "30 days + 1 minute", 401),
        (1, "1 day + 1 minute", 401),  # a shorter retention shortens the credential's life
        (1, "23 hours", 200),
    ],
)
async def test_retention_edge(retention_days: int, inactive_for: str, status: int) -> None:
    app = make_app(guest_retention_days=retention_days)
    async with client_for(app, lifespan=True) as client:
        guest = await new_guest(client)
        await sql(
            app,
            "UPDATE principals SET last_activity_at = now() - CAST(:age AS interval)"
            " WHERE id = :id",
            age=inactive_for,
            id=principal_of(guest),
        )

        response = await client.post(GUEST, json={"guest_credential": guest["guest_credential"]})

    assert response.status_code == status


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"guest_credential": ""},
        {"guest_credential": "x" * 257},
        {"guest_credential": 1},
        {"guest_credential": "x" * 43, "device_id": "abc"},
    ],
    ids=["empty object", "empty", "too long", "not a string", "extra field"],
)
async def test_invalid_body_gets_422(client: httpx.AsyncClient, body: dict[str, Any]) -> None:
    response = await client.post(GUEST, json=body)

    assert response.status_code == 422
    assert_matches_contract(response, GUEST, "post")


@pytest.mark.parametrize(
    ("raw", "status"),
    [(b"null", 422), (b" ", 422), (b"", 201)],
    ids=["json null", "whitespace", "empty is absent"],
)
async def test_only_an_absent_or_empty_body_creates_a_guest(
    app: FastAPI, client: httpx.AsyncClient, raw: bytes, status: int
) -> None:
    before = await sql(app, "SELECT count(*) FROM principals")

    response = await client.post(GUEST, content=raw, headers={"Content-Type": "application/json"})

    assert response.status_code == status
    assert_matches_contract(response, GUEST, "post")
    after = await sql(app, "SELECT count(*) FROM principals")
    assert after[0][0] - before[0][0] == (1 if status == 201 else 0)
    if raw == b"null":
        assert response.json()["errors"] == [
            {"loc": ["body"], "msg": "Input should be an object", "type": "model_type"}
        ]


async def test_principals_store_no_personal_data(app: FastAPI) -> None:
    async with client_for(app, lifespan=True):
        rows = await sql(
            app,
            "SELECT table_name, column_name FROM information_schema.columns"
            " WHERE table_schema = current_schema() AND table_name = 'principals'",
        )

    assert {column for _, column in rows} == {"id", "kind", "created_at", "last_activity_at"}


async def test_a4_no_raw_credential_or_token_in_any_auth_column(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    guest = await new_guest(client)
    signed_in = (
        await client.post(GUEST, json={"guest_credential": guest["guest_credential"]})
    ).json()
    raws = [guest["guest_credential"], guest["refresh_token"], signed_in["refresh_token"]]

    dump = ""
    for table in AUTH_TABLES:
        rows = await sql(app, f"SELECT row_to_json(t)::text FROM {table} t")  # noqa: S608 - fixed names
        dump += "\n".join(row[0] for row in rows)

    for raw in raws:
        assert raw not in dump
        assert raw.encode().hex() not in dump


# --- current principal ---


async def test_dependency_takes_kind_from_the_row_not_the_claim(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    principal = principal_of(await new_guest(client))
    token = app.state.tokens.issue_access(principal, "account")

    response = await client.get(ME, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"id": str(principal), "kind": "guest"}


async def test_deleted_principal_gets_401(app: FastAPI, client: httpx.AsyncClient) -> None:
    guest = await new_guest(client)
    await sql(app, "DELETE FROM principals WHERE id = :id", id=principal_of(guest))

    response = await client.get(ME, headers={"Authorization": f"Bearer {guest['access_token']}"})

    assert_unauthorized(response)


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "Basic dXNlcjpwYXNz",
        "Bearer",
        "Bearer ",
        "bearer not-a-token",
        f"Bearer {forge({'alg': 'none', 'kid': TEST_SIGNING_KEYS[0].kid, 'typ': 'at+jwt'})}",
        f"Bearer {forge({'alg': 'HS256', 'kid': '2020-01-01', 'typ': 'at+jwt'})}",
        f"Bearer {forge(claims=valid_claims(exp=1))}",
        f"Bearer {forge(key=b'-----BEGIN PUBLIC KEY-----')}",
    ],
    ids=[
        "missing",
        "basic",
        "no token",
        "empty token",
        "garbage",
        "alg none",
        "unknown kid",
        "expired",
        "pem key",
    ],
)
async def test_every_auth_failure_gets_the_same_401(
    client: httpx.AsyncClient, authorization: str | None
) -> None:
    headers = {} if authorization is None else {"Authorization": authorization}

    response = await client.get(ME, headers=headers)

    assert_unauthorized(response)


async def test_r5_oversized_token_gets_401_before_parsing(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    principal = str(principal_of(await new_guest(client)))
    # Correctly signed for a live principal: only the length can reject the padded one.
    normal = forge(claims=valid_claims(sub=principal))
    oversized = forge(claims=valid_claims(sub=principal, pad="x" * 1024))

    ok = await client.get(ME, headers={"Authorization": f"Bearer {normal}"})
    refused = await client.get(ME, headers={"Authorization": f"Bearer {oversized}"})

    assert ok.status_code == 200
    assert len(oversized) > 1024
    assert_unauthorized(refused)


# --- last_activity_at (ADR-022) ---


async def _set_inactive(app: FastAPI, principal: uuid.UUID, age: str) -> None:
    await sql(
        app,
        "UPDATE principals SET last_activity_at = now() - CAST(:age AS interval) WHERE id = :id",
        age=age,
        id=principal,
    )


async def _recently_active(app: FastAPI, principal: uuid.UUID) -> bool:
    rows = await sql(
        app,
        "SELECT last_activity_at > now() - interval '1 minute' FROM principals WHERE id = :id",
        id=principal,
    )
    return bool(rows[0][0])


@pytest.mark.parametrize(
    ("age", "query", "status", "touched"),
    [
        ("2 hours", "", 200, True),
        ("2 hours", "?fail=true", 404, False),  # authenticated, then a handled error
        ("2 hours", "?crash=true", 500, False),  # authenticated, then an unhandled error
        ("30 minutes", "", 200, False),  # hourly cap
    ],
)
async def test_last_activity_is_touched_only_after_a_2xx_and_at_most_hourly(
    app: FastAPI, client: httpx.AsyncClient, age: str, query: str, status: int, touched: bool
) -> None:
    guest = await new_guest(client)
    principal = principal_of(guest)
    await _set_inactive(app, principal, age)

    response = await client.get(
        ME + query, headers={"Authorization": f"Bearer {guest['access_token']}"}
    )

    assert response.status_code == status
    assert await _recently_active(app, principal) is touched


async def test_guest_sign_in_counts_as_activity(app: FastAPI, client: httpx.AsyncClient) -> None:
    guest = await new_guest(client)
    principal = principal_of(guest)
    await _set_inactive(app, principal, "2 hours")

    await client.post(GUEST, json={"guest_credential": guest["guest_credential"]})

    assert await _recently_active(app, principal)


async def test_failed_touch_is_logged_without_parameters_and_keeps_the_2xx(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def broken(*_: object) -> None:
        raise OperationalError("UPDATE principals ...", {"id": "secret-param"}, OSError())

    monkeypatch.setattr("modules.auth.repository.touch_last_activity", broken)
    app = make_app()  # after capsys, so the JSON handler writes to the captured stdout
    async with client_for(app, lifespan=True) as client:
        guest = await new_guest(client)
        response = await client.get(
            ME, headers={"Authorization": f"Bearer {guest['access_token']}"}
        )

    assert response.status_code == 200
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    failed = [line for line in lines if line["msg"] == "last activity update failed"]
    assert len(failed) == 1
    assert failed[0]["error"] == "OperationalError"
    assert "secret-param" not in json.dumps(lines)


# --- logs (docs/security.md §6, A15) ---


async def test_logs_hold_no_secrets_and_a15_events_carry_the_principal(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = make_app()  # after capsys, so the JSON handler writes to the captured stdout
    async with client_for(app, lifespan=True) as client:
        guest = await new_guest(client)
        signed_in = (
            await client.post(GUEST, json={"guest_credential": guest["guest_credential"]})
        ).json()

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    principal = str(principal_of(guest))
    events = [(line["event"], line["principal_id"]) for line in lines if line["logger"] == A15]
    assert events == [("guest_created", principal), ("guest_signed_in", principal)]
    raw = json.dumps(lines)
    for secret in (*guest.values(), *signed_in.values()):
        if isinstance(secret, str) and len(secret) > 20:
            assert secret not in raw
            assert hashlib.sha256(secret.encode()).hexdigest() not in raw
    assert "127.0.0.1" not in raw


async def test_slow_touch_is_cut_by_the_statement_timeout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = make_app()  # after capsys, so the JSON handler writes to the captured stdout
    async with client_for(app, lifespan=True) as client:
        guest = await new_guest(client)
        principal = principal_of(guest)
        await _set_inactive(app, principal, "2 hours")
        blocker = await app.state.engine.connect()
        try:
            # Hold the row lock: the touch waits until its 2 s statement timeout cancels it.
            await blocker.begin()
            await blocker.execute(
                text("SELECT 1 FROM principals WHERE id = :id FOR UPDATE"), {"id": principal}
            )
            started = time.perf_counter()
            # Without the statement timeout the touch would wait for the lock forever.
            async with asyncio.timeout(5):
                response = await client.get(
                    ME, headers={"Authorization": f"Bearer {guest['access_token']}"}
                )
            elapsed = time.perf_counter() - started
        finally:
            await blocker.rollback()
            await blocker.close()

    assert response.status_code == 200
    assert elapsed > 1.5
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    failed = [line for line in lines if line["msg"] == "last activity update failed"]
    assert [line["error"] for line in failed] == ["OperationalError"]
