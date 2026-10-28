"""Refresh rotation, the grace rule and logout against real Postgres (E1-05c, ADR-014)."""

import asyncio
import base64
import hashlib
import json
import os
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from core.config import database_url_from_env
from tests.integration.test_auth import (
    AUTH_TABLES,
    ME,
    assert_unauthorized,
    make_app,
    new_guest,
    principal_of,
    without_request_id,
)
from tests.support import assert_matches_contract, client_for

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

REFRESH = "/v1/auth/refresh"
LOGOUT = "/v1/auth/logout"


@pytest.fixture
async def app() -> AsyncIterator[FastAPI]:
    yield make_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with client_for(app, lifespan=True) as client:
        yield client


@pytest.fixture
async def observer() -> AsyncIterator[AsyncEngine]:
    """Connections of its own, never the app's pool: what it reads has been committed."""
    engine = create_async_engine(database_url_from_env(os.environ), poolclass=NullPool)
    yield engine
    await engine.dispose()


def h(raw: str) -> bytes:
    return hashlib.sha256(raw.encode()).digest()


async def sql(engine: AsyncEngine, query: str, **params: object) -> list[Any]:
    async with engine.begin() as conn:
        result = await conn.execute(text(query), params)
        return list(result.all()) if result.returns_rows else []


async def refresh(client: httpx.AsyncClient, token: str) -> httpx.Response:
    return await client.post(REFRESH, json={"refresh_token": token})


async def family_of(engine: AsyncEngine, token: str) -> dict[str, Any]:
    rows = await sql(
        engine,
        "SELECT f.id, f.revoked_at IS NOT NULL AS revoked,"
        " f.last_refreshed_at > now() - interval '1 minute' AS refreshed_now"
        " FROM refresh_families f JOIN refresh_tokens t ON t.family_id = f.id"
        " WHERE t.token_hash = :hash",
        hash=h(token),
    )
    return dict(rows[0]._mapping)


async def states(engine: AsyncEngine, family_id: object) -> dict[bytes, str]:
    rows = await sql(
        engine, "SELECT token_hash, state FROM refresh_tokens WHERE family_id = :id", id=family_id
    )
    return {bytes(row[0]): row[1] for row in rows}


async def age_family(engine: AsyncEngine, token: str, column: str, age: str) -> None:
    family = await family_of(engine, token)
    await sql(
        engine,
        f"UPDATE refresh_families SET {column} = now() - CAST(:age AS interval) WHERE id = :id",  # noqa: S608 - fixed names
        age=age,
        id=family["id"],
    )


async def set_rotated_age(engine: AsyncEngine, token: str, age: str) -> None:
    await sql(
        engine,
        "UPDATE refresh_tokens SET rotated_at = now() - CAST(:age AS interval)"
        " WHERE token_hash = :hash",
        age=age,
        hash=h(token),
    )


async def rotated_once(
    client: httpx.AsyncClient, observer: AsyncEngine
) -> tuple[dict[str, Any], str, str]:
    """A guest whose first refresh token was rotated: (guest, old token, its successor)."""
    guest = await new_guest(client)
    response = await refresh(client, guest["refresh_token"])
    assert response.status_code == 200, response.text
    return guest, guest["refresh_token"], response.json()["refresh_token"]


# --- rotation ---


async def test_refresh_rotates_and_returns_a_working_pair(
    app: FastAPI, client: httpx.AsyncClient, observer: AsyncEngine
) -> None:
    guest = await new_guest(client)
    old = guest["refresh_token"]
    await age_family(observer, old, "last_refreshed_at", "1 day")

    response = await refresh(client, old)

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert_matches_contract(response, REFRESH, "post")
    new = response.json()["refresh_token"]
    assert new != old
    family = await family_of(observer, old)
    assert family["refreshed_now"] and not family["revoked"]
    assert await states(observer, family["id"]) == {h(old): "rotated", h(new): "current"}
    successor = await sql(
        observer, "SELECT successor_hash FROM refresh_tokens WHERE token_hash = :h", h=h(old)
    )
    assert bytes(successor[0][0]) == h(new)
    access = response.json()["access_token"]
    me = await client.get(ME, headers={"Authorization": f"Bearer {access}"})
    assert me.json() == {"id": str(principal_of(guest)), "kind": "guest"}

    again = await refresh(client, new)  # the successor rotates in turn

    assert again.status_code == 200


async def test_refresh_takes_kind_from_the_row(
    client: httpx.AsyncClient, observer: AsyncEngine
) -> None:
    guest = await new_guest(client)
    # An account is not bound by the guest retention.
    await sql(
        observer,
        "UPDATE principals SET kind = 'account', last_activity_at = now() - interval '60 days'"
        " WHERE id = :id",
        id=principal_of(guest),
    )

    response = await refresh(client, guest["refresh_token"])

    assert response.status_code == 200
    claims = response.json()["access_token"].split(".")[1]
    assert json.loads(base64.urlsafe_b64decode(claims + "=="))["kind"] == "account"


# --- the one 401 ---


@pytest.mark.parametrize(
    "setup",
    [
        "UPDATE refresh_families SET revoked_at = now() WHERE id = :family",
        "UPDATE refresh_families SET last_refreshed_at = now() - interval '30 days 1 minute'"
        " WHERE id = :family",
        "UPDATE refresh_families SET created_at = now() - interval '90 days 1 minute'"
        " WHERE id = :family",
        "UPDATE principals SET last_activity_at = now() - interval '30 days 1 minute'"
        " WHERE id = :principal",
    ],
    ids=["revoked", "idle over 30 days", "older than 90 days", "guest past retention"],
)
async def test_dead_unknown_and_malformed_tokens_get_the_same_401_and_revoke_nothing(
    client: httpx.AsyncClient, observer: AsyncEngine, setup: str
) -> None:
    guest = await new_guest(client)
    family = await family_of(observer, guest["refresh_token"])
    await sql(observer, setup, family=family["id"], principal=principal_of(guest))
    revoked_before = (await family_of(observer, guest["refresh_token"]))["revoked"]
    other = await new_guest(client)  # a live family nobody touches
    total_revoked = "SELECT count(*) FROM refresh_families WHERE revoked_at IS NOT NULL"
    revoked_count = await sql(observer, total_revoked)

    dead = await refresh(client, guest["refresh_token"])
    unknown = await refresh(client, "x" * 43)
    malformed = await refresh(client, "not a token ?!")

    for response in (dead, unknown, malformed):
        assert_unauthorized(response)
        assert_matches_contract(response, REFRESH, "post")
    assert without_request_id(dead) == without_request_id(unknown) == without_request_id(malformed)
    assert dict(dead.headers) | {"x-request-id": ""} == dict(unknown.headers) | {"x-request-id": ""}
    assert (await family_of(observer, guest["refresh_token"]))["revoked"] is revoked_before
    assert await sql(observer, total_revoked) == revoked_count
    assert (await refresh(client, other["refresh_token"])).status_code == 200


@pytest.mark.parametrize(
    ("column", "age"),
    [("last_refreshed_at", "29 days 23 hours"), ("created_at", "89 days 23 hours")],
)
async def test_family_limits_inside_the_edge(
    client: httpx.AsyncClient, observer: AsyncEngine, column: str, age: str
) -> None:
    guest = await new_guest(client)
    await age_family(observer, guest["refresh_token"], column, age)

    assert (await refresh(client, guest["refresh_token"])).status_code == 200


@pytest.mark.parametrize(
    ("retention_days", "inactive_for", "status"),
    [(1, "1 day 1 minute", 401), (1, "23 hours", 200)],
)
async def test_refresh_follows_the_configured_guest_retention(
    observer: AsyncEngine, retention_days: int, inactive_for: str, status: int
) -> None:
    app = make_app(guest_retention_days=retention_days)
    async with client_for(app, lifespan=True) as client:
        guest = await new_guest(client)
        await sql(
            observer,
            "UPDATE principals SET last_activity_at = now() - CAST(:age AS interval)"
            " WHERE id = :id",
            age=inactive_for,
            id=principal_of(guest),
        )

        response = await refresh(client, guest["refresh_token"])

    assert response.status_code == status


@pytest.mark.parametrize("path", [REFRESH, LOGOUT])
@pytest.mark.parametrize(
    "body",
    [{}, {"refresh_token": ""}, {"refresh_token": "x" * 257}, {"refresh_token": 1}, None],
    ids=["missing", "empty", "too long", "not a string", "no body"],
)
async def test_invalid_body_gets_422(
    client: httpx.AsyncClient, path: str, body: dict[str, Any] | None
) -> None:
    response = await client.post(path, json=body)

    assert response.status_code == 422
    assert_matches_contract(response, path, "post")


# --- grace rule (R6) and reuse detection ---


async def test_grace_inside_the_window_supersedes_the_successor(
    client: httpx.AsyncClient, observer: AsyncEngine
) -> None:
    _, old, lost = await rotated_once(client, observer)
    await set_rotated_age(observer, old, "29 seconds")
    await age_family(observer, old, "last_refreshed_at", "1 day")

    response = await refresh(client, old)

    assert response.status_code == 200
    assert_matches_contract(response, REFRESH, "post")
    new = response.json()["refresh_token"]
    family = await family_of(observer, old)
    assert family["refreshed_now"] and not family["revoked"]
    assert await states(observer, family["id"]) == {
        h(old): "rotated",
        h(lost): "superseded",
        h(new): "current",
    }
    grace = await sql(
        observer,
        "SELECT grace_used_at IS NOT NULL, rotated_at < now() - interval '28 seconds'"
        " FROM refresh_tokens WHERE token_hash = :h",
        h=h(old),
    )
    assert grace == [(True, True)]  # first rotation time kept
    assert (await refresh(client, new)).status_code == 200


async def _assert_revoked(
    client: httpx.AsyncClient, observer: AsyncEngine, response: httpx.Response, *tokens: str
) -> None:
    assert_unauthorized(response)
    assert_matches_contract(response, REFRESH, "post")
    # Read on a connection of its own: the revocation was committed before the 401.
    assert (await family_of(observer, tokens[0]))["revoked"]
    for token in tokens:
        assert_unauthorized(await refresh(client, token))


async def test_grace_just_outside_the_window_revokes_the_family(
    client: httpx.AsyncClient, observer: AsyncEngine
) -> None:
    _, old, successor = await rotated_once(client, observer)
    await set_rotated_age(observer, old, "31 seconds")

    response = await refresh(client, old)

    await _assert_revoked(client, observer, response, old, successor)


async def test_second_grace_attempt_revokes_the_family(
    client: httpx.AsyncClient, observer: AsyncEngine
) -> None:
    _, old, _ = await rotated_once(client, observer)
    graced = await refresh(client, old)
    assert graced.status_code == 200

    response = await refresh(client, old)

    await _assert_revoked(client, observer, response, old, graced.json()["refresh_token"])


async def test_superseded_successor_coming_back_revokes_the_family(
    client: httpx.AsyncClient, observer: AsyncEngine
) -> None:
    _, old, lost = await rotated_once(client, observer)
    graced = await refresh(client, old)
    assert graced.status_code == 200

    response = await refresh(client, lost)

    await _assert_revoked(client, observer, response, lost, graced.json()["refresh_token"])


async def test_grace_after_the_successor_rotated_revokes_the_family(
    client: httpx.AsyncClient, observer: AsyncEngine
) -> None:
    _, old, successor = await rotated_once(client, observer)
    newest = await refresh(client, successor)
    assert newest.status_code == 200

    response = await refresh(client, old)  # inside 30 s, but its successor is no longer current

    await _assert_revoked(client, observer, response, old, newest.json()["refresh_token"])


# --- concurrency: real connections queued on the family lock ---


async def _hold_family_lock(observer: AsyncEngine, token: str) -> tuple[AsyncConnection, int]:
    """A connection holding the family row lock, and its backend pid."""
    conn = await observer.connect()
    await conn.begin()
    pid = (await conn.execute(text("SELECT pg_backend_pid()"))).scalar_one()
    await conn.execute(
        text(
            "SELECT 1 FROM refresh_families f JOIN refresh_tokens t ON t.family_id = f.id"
            " WHERE t.token_hash = :hash FOR UPDATE OF f"
        ),
        {"hash": h(token)},
    )
    return conn, pid


# Waiters behind the first one queue on its tuple lock, so they name it, not the blocker.
_BLOCKED_BY = """
    WITH RECURSIVE blocked(pid) AS (
        SELECT pid FROM pg_stat_activity WHERE CAST(:blocker AS int) = ANY(pg_blocking_pids(pid))
        UNION
        SELECT a.pid FROM pg_stat_activity a JOIN blocked b ON b.pid = ANY(pg_blocking_pids(a.pid))
    )
    SELECT count(*) FROM blocked
"""


async def _wait_for_lock_waiters(observer: AsyncEngine, blocker: int, count: int) -> None:
    """Until `count` backends wait on the blocker, directly or behind another waiter."""
    for _ in range(50):  # about 1 s, well inside the 2 s lock_timeout; polls another process
        if (await sql(observer, _BLOCKED_BY, blocker=blocker))[0][0] >= count:
            return
        await asyncio.sleep(0.02)
    pytest.fail(f"fewer than {count} requests queued on the family lock")


@pytest.mark.parametrize("requests", [2, 3])
async def test_concurrent_refreshes_with_the_same_token(
    client: httpx.AsyncClient, observer: AsyncEngine, requests: int
) -> None:
    guest = await new_guest(client)
    token = guest["refresh_token"]
    blocker, pid = await _hold_family_lock(observer, token)
    try:
        tasks = [asyncio.create_task(refresh(client, token)) for _ in range(requests)]
        await _wait_for_lock_waiters(observer, pid, requests)  # each on a connection of its own
    finally:
        await blocker.rollback()
        await blocker.close()
    responses = await asyncio.gather(*tasks)

    family = await family_of(observer, token)
    by_status = sorted(r.status_code for r in responses)
    issued = [h(r.json()["refresh_token"]) for r in responses if r.status_code == 200]
    tokens = await states(observer, family["id"])
    graced = await sql(
        observer,
        "SELECT grace_used_at IS NOT NULL FROM refresh_tokens WHERE token_hash = :h",
        h=h(token),
    )
    assert graced == [(True,)]
    assert sorted(tokens[i] for i in issued) == ["current", "superseded"]
    if requests == 2:
        assert by_status == [200, 200]
        assert list(tokens.values()).count("current") == 1
        assert not family["revoked"]
    else:
        assert by_status == [200, 200, 401]
        assert family["revoked"]


# --- lock timeout: 503, nothing changed, a retry works ---


async def test_lock_timeout_gets_503_and_the_retry_works(
    client: httpx.AsyncClient, observer: AsyncEngine
) -> None:
    guest = await new_guest(client)
    token = guest["refresh_token"]
    family = await family_of(observer, token)
    blocker, _ = await _hold_family_lock(observer, token)
    try:
        started = time.perf_counter()
        # A lost lock_timeout must fail the test, not hang it.
        busy_refresh = await asyncio.wait_for(refresh(client, token), 5)
        elapsed = time.perf_counter() - started
        busy_logout = await asyncio.wait_for(client.post(LOGOUT, json={"refresh_token": token}), 5)
    finally:
        await blocker.rollback()
        await blocker.close()

    assert 1.9 < elapsed < 4
    for response, path in ((busy_refresh, REFRESH), (busy_logout, LOGOUT)):
        assert response.status_code == 503
        assert response.headers["Retry-After"] == "1"
        assert without_request_id(response) == {
            "type": "about:blank",
            "title": "Service Unavailable",
            "status": 503,
        }
        assert_matches_contract(response, path, "post")
    assert await states(observer, family["id"]) == {h(token): "current"}
    assert not (await family_of(observer, token))["revoked"]

    retried = await refresh(client, token)

    assert retried.status_code == 200
    logout = await client.post(LOGOUT, json={"refresh_token": retried.json()["refresh_token"]})
    assert logout.status_code == 204
    assert (await family_of(observer, token))["revoked"]


# --- logout ---


async def test_logout_revokes_only_this_family_and_always_gets_204(
    client: httpx.AsyncClient, observer: AsyncEngine
) -> None:
    guest = await new_guest(client)
    other = await client.post(
        "/v1/auth/guest", json={"guest_credential": guest["guest_credential"]}
    )  # a second device of the same guest
    token = guest["refresh_token"]

    first = await client.post(LOGOUT, json={"refresh_token": token})

    assert first.status_code == 204
    assert_matches_contract(first, LOGOUT, "post")
    assert (await family_of(observer, token))["revoked"]
    assert_unauthorized(await refresh(client, token))
    for again in (token, "x" * 43, "not a token ?!"):  # revoked, unknown, malformed
        response = await client.post(LOGOUT, json={"refresh_token": again})
        assert response.status_code == 204
        assert response.content == b""
    assert (await refresh(client, other.json()["refresh_token"])).status_code == 200


@pytest.mark.parametrize("presented", ["rotated", "superseded"])
async def test_logout_with_a_used_token_revokes_and_is_logged_as_reuse(
    capsys: pytest.CaptureFixture[str], observer: AsyncEngine, presented: str
) -> None:
    app = make_app()  # after capsys, so the JSON handler writes to the captured stdout
    async with client_for(app, lifespan=True) as client:
        guest, old, lost = await rotated_once(client, observer)
        graced = await refresh(client, old)  # `lost` becomes superseded
        assert graced.status_code == 200
        used = old if presented == "rotated" else lost

        response = await client.post(LOGOUT, json={"refresh_token": used})

        assert response.status_code == 204
        assert (await family_of(observer, used))["revoked"]
        assert_unauthorized(await refresh(client, graced.json()["refresh_token"]))

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    principal = str(principal_of(guest))
    events = [
        (line["event"], line["principal_id"], line.get("reason"))
        for line in lines
        if line.get("event") in {"reuse_detected", "family_revoked"}
    ]
    assert events == [
        ("reuse_detected", principal, None),
        ("family_revoked", principal, "reuse"),
    ]
    assert used not in json.dumps(lines)


# --- last_activity_at (ADR-022) ---


async def _activity_after(
    client: httpx.AsyncClient, observer: AsyncEngine, age: str, call: str
) -> bool:
    guest = await new_guest(client)
    principal = principal_of(guest)
    token = guest["refresh_token"]
    if call == "reuse":  # rotate, then use the grace: the next use of `token` is a reuse
        assert (await refresh(client, token)).status_code == 200
        assert (await refresh(client, token)).status_code == 200
    await sql(
        observer,
        "UPDATE principals SET last_activity_at = now() - CAST(:age AS interval) WHERE id = :id",
        age=age,
        id=principal,
    )
    if call == "logout":
        assert (await client.post(LOGOUT, json={"refresh_token": token})).status_code == 204
    else:
        # The measured call itself: the 2xx refresh, or the reuse 401 that revokes the family.
        expected = 401 if call == "reuse" else 200
        assert (await refresh(client, token)).status_code == expected
    if call == "reuse":
        assert (await family_of(observer, token))["revoked"]
    rows = await sql(
        observer,
        "SELECT last_activity_at > now() - interval '1 minute' FROM principals WHERE id = :id",
        id=principal,
    )
    return bool(rows[0][0])


@pytest.mark.parametrize(
    ("age", "call", "touched"),
    [
        ("2 hours", "refresh", True),
        ("30 minutes", "refresh", False),  # hourly cap
        ("2 hours", "reuse", False),  # a 401 is not activity
        ("2 hours", "logout", False),  # logout is not activity
    ],
)
async def test_last_activity_after_refresh_and_logout(
    client: httpx.AsyncClient, observer: AsyncEngine, age: str, call: str, touched: bool
) -> None:
    assert await _activity_after(client, observer, age, call) is touched


# --- A4 and A15 ---


async def test_a4_only_hashes_are_stored_for_rotated_superseded_and_new_tokens(
    client: httpx.AsyncClient, observer: AsyncEngine
) -> None:
    _, old, lost = await rotated_once(client, observer)
    new = (await refresh(client, old)).json()["refresh_token"]

    family = await family_of(observer, old)
    assert await states(observer, family["id"]) == {
        h(old): "rotated",
        h(lost): "superseded",
        h(new): "current",
    }
    dump = ""
    for table in AUTH_TABLES:
        rows = await sql(observer, f"SELECT row_to_json(t)::text FROM {table} t")  # noqa: S608 - fixed names
        dump += "\n".join(row[0] for row in rows)
    for raw in (old, lost, new):
        assert raw not in dump
        assert raw.encode().hex() not in dump


async def test_a15_events_carry_the_principal_and_no_secret(
    capsys: pytest.CaptureFixture[str], observer: AsyncEngine
) -> None:
    app = make_app()  # after capsys, so the JSON handler writes to the captured stdout
    async with client_for(app, lifespan=True) as client:
        guest, old, lost = await rotated_once(client, observer)
        graced = (await refresh(client, old)).json()
        await refresh(client, old)  # reuse
        sign_in = {"guest_credential": guest["guest_credential"]}
        second = (await client.post("/v1/auth/guest", json=sign_in)).json()
        await client.post(LOGOUT, json={"refresh_token": second["refresh_token"]})
        await client.post(LOGOUT, json={"refresh_token": "x" * 43})  # unknown: no event

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    principal = str(principal_of(guest))
    events = [
        (line["event"], line["principal_id"], line.get("reason"))
        for line in lines
        if "event" in line and line["event"] not in {"guest_created", "guest_signed_in"}
    ]
    assert events == [
        ("grace_used", principal, None),
        ("reuse_detected", principal, None),
        ("family_revoked", principal, "reuse"),
        ("family_revoked", principal, "logout"),
    ]
    raw = json.dumps(lines)
    for secret in (old, lost, graced["refresh_token"], second["refresh_token"]):
        assert secret not in raw
        assert hashlib.sha256(secret.encode()).hexdigest() not in raw
        assert secret.encode().hex() not in raw
    assert "127.0.0.1" not in raw
