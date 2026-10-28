"""Sign-up, sign-in and account logout against real Postgres and the real hasher (E1-07)."""

import asyncio
import hashlib
import json
import statistics
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from argon2 import PasswordHasher, Type
from fastapi import FastAPI

from core import db_errors
from modules.auth import hashing, service
from modules.auth.hashing import PasswordHashing, Verified
from tests.integration.test_auth import (
    ME,
    assert_unauthorized,
    make_app,
    principal_of,
    sql,
    without_request_id,
)
from tests.support import BlockingHasher, assert_matches_contract, client_for, fill_hash_slots

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

SIGN_UP = "/v1/auth/sign-up"
SIGN_IN = "/v1/auth/sign-in"
REFRESH = "/v1/auth/refresh"
LOGOUT = "/v1/auth/logout"
PASSWORD = "violet hedgehog 42"  # noqa: S105 - made-up test passwords
WRONG = "violet hedgehog 43"
OTHER = "another password 77"
COMMON = "123456789012"
EMAIL_REGISTERED = {
    "type": "urn:capsule:problem:email-registered",
    "title": "Conflict",
    "status": 409,
    "detail": "An account with this email exists. Sign in instead.",
}


def new_email() -> str:
    """A made-up address on the reserved example.com domain, unique per test."""
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
async def app() -> AsyncIterator[FastAPI]:
    yield make_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with client_for(app, lifespan=True) as client:
        yield client


async def sign_up(
    client: httpx.AsyncClient, email: str, password: str = PASSWORD
) -> httpx.Response:
    body = {"email": email, "password": password, "age_confirmed": True}
    return await client.post(SIGN_UP, json=body)


async def sign_in(
    client: httpx.AsyncClient, email: str, password: str = PASSWORD
) -> httpx.Response:
    return await client.post(SIGN_IN, json={"email": email, "password": password})


async def account_row(app: FastAPI, email: str) -> Any:
    rows = await sql(
        app,
        "SELECT a.principal_id, a.password_hash, a.age_confirmed_at, a.created_at, p.kind"
        " FROM accounts a JOIN principals p ON p.id = a.principal_id WHERE a.email = :email",
        email=email,
    )
    return rows[0] if rows else None


# --- sign-up ---


async def test_sign_up_creates_an_account_and_its_first_session(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    email = new_email()
    response = await sign_up(client, f"  {email.upper()} ")

    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"
    assert_matches_contract(response, SIGN_UP, "post")
    body = response.json()
    row = await account_row(app, email)  # stored normalised
    assert row.principal_id == principal_of(body)
    assert row.kind == "account"
    assert row.password_hash.startswith("$argon2id$v=19$m=65536,t=3,p=1$")
    assert PASSWORD not in row.password_hash
    assert abs((row.age_confirmed_at - row.created_at).total_seconds()) < 1
    me = await client.get(ME, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json() == {"id": str(row.principal_id), "kind": "account"}
    refreshed = await client.post(REFRESH, json={"refresh_token": body["refresh_token"]})
    assert refreshed.status_code == 200


async def test_accounts_hold_no_birth_date_or_other_personal_column(app: FastAPI) -> None:
    async with client_for(app, lifespan=True):
        columns = await sql(
            app,
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'accounts'",
        )
    assert {c.column_name for c in columns} == {
        "principal_id",
        "email",
        "password_hash",
        "age_confirmed_at",
        "created_at",
    }


@pytest.mark.parametrize(
    "extra",
    [{}, {"age_confirmed": False}, {"age_confirmed": 1}, {"age_confirmed": "true"}],
    ids=["missing", "false", "one", "string"],
)
async def test_sign_up_without_age_confirmation_gets_422_and_creates_nothing(
    app: FastAPI, client: httpx.AsyncClient, extra: dict[str, Any]
) -> None:
    email = new_email()
    response = await client.post(SIGN_UP, json={"email": email, "password": PASSWORD} | extra)

    assert response.status_code == 422
    assert_matches_contract(response, SIGN_UP, "post")
    assert [e["loc"] for e in response.json()["errors"]] == [["body", "age_confirmed"]]
    assert await account_row(app, email) is None


async def test_a_refused_password_gets_422_without_the_value(client: httpx.AsyncClient) -> None:
    email = new_email()
    response = await sign_up(client, email, password=COMMON)

    assert response.status_code == 422
    assert [e["type"] for e in response.json()["errors"]] == ["password_common"]
    assert COMMON not in response.text
    assert email not in response.text


async def test_registered_email_in_another_case_gets_the_a7_conflict(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    email = new_email()
    assert (await sign_up(client, email)).status_code == 201
    principals_before = await sql(app, "SELECT count(*) AS n FROM principals")

    conflict = await sign_up(client, f" {email.upper()}", password=OTHER)

    assert conflict.status_code == 409
    assert conflict.headers["content-type"] == "application/problem+json"
    assert without_request_id(conflict) == EMAIL_REGISTERED
    assert_matches_contract(conflict, SIGN_UP, "post")
    assert await sql(app, "SELECT count(*) AS n FROM principals") == principals_before


async def test_two_parallel_sign_ups_with_one_email_get_one_201_and_one_409(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    backstop_hits: list[bool] = []

    def spy(exc: BaseException, constraint: str) -> bool:
        backstop_hits.append(db_errors.is_unique_violation(exc, constraint))
        return backstop_hits[-1]

    monkeypatch.setattr(service, "is_unique_violation", spy)
    app = make_app()  # after capsys, so the JSON handler writes to the captured stdout
    email = new_email()
    async with client_for(app, lifespan=True) as client:
        # The barrier holds each request at its hash until both have done the check before
        # insert, so both pass it and the second insert always hits the unique constraint, which
        # must answer the same 409 and log nothing about the email.
        app.state.password_hashing = _BarrierBeforeHash(app.state.password_hashing)
        first, second = await asyncio.gather(sign_up(client, email), sign_up(client, email))
        rows = await sql(app, "SELECT count(*) AS n FROM accounts WHERE email = :e", e=email)

    assert sorted([first.status_code, second.status_code]) == [201, 409]
    conflict = first if first.status_code == 409 else second
    assert without_request_id(conflict) == EMAIL_REGISTERED
    assert rows[0].n == 1
    assert backstop_hits == [True]  # the 409 came from the unique constraint, not the check
    out = capsys.readouterr().out
    assert email not in out
    assert "accounts_email_key" not in out  # the backstop is silent: a 409 is not an error


async def test_sign_up_answers_503_when_every_hash_slot_stays_taken(
    app: FastAPI, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hashing, "ACQUIRE_TIMEOUT_S", 0.2)
    fake = BlockingHasher()
    monkeypatch.setattr(hashing, "_HASHER", fake)
    email = new_email()
    tasks = await fill_hash_slots(app.state.password_hashing, fake)
    try:
        busy = await sign_up(client, email)
        busy_sign_in = await sign_in(client, email)
    finally:
        fake.release.set()
        await asyncio.gather(*tasks)

    for response, path in ((busy, SIGN_UP), (busy_sign_in, SIGN_IN)):
        assert response.status_code == 503
        assert response.headers["Retry-After"] == "1"
        assert_matches_contract(response, path, "post")
    assert fake.started == hashing.SLOTS  # neither request ran a hash
    assert await account_row(app, email) is None


# --- sign-in ---


async def test_sign_in_starts_a_new_session_and_counts_as_activity(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    email = new_email()
    created = (await sign_up(client, email)).json()
    principal = principal_of(created)
    await sql(
        app,
        "UPDATE principals SET last_activity_at = now() - interval '2 hours' WHERE id = :id",
        id=principal,
    )

    response = await sign_in(client, email.upper())

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert_matches_contract(response, SIGN_IN, "post")
    assert principal_of(response.json()) == principal
    assert response.json()["refresh_token"] != created["refresh_token"]
    families = await sql(
        app, "SELECT count(*) AS n FROM refresh_families WHERE principal_id = :id", id=principal
    )
    assert families[0].n == 2
    active = await sql(
        app,
        "SELECT last_activity_at > now() - interval '1 minute' AS recent FROM principals"
        " WHERE id = :id",
        id=principal,
    )
    assert active[0].recent


async def test_wrong_password_unknown_and_invalid_email_get_one_401(
    client: httpx.AsyncClient,
) -> None:
    email = new_email()
    assert (await sign_up(client, email)).status_code == 201

    wrong_password = await sign_in(client, email, password=WRONG)
    unknown_email = await sign_in(client, new_email())
    invalid_email = await sign_in(client, "not an email")
    too_long = await sign_in(client, email, password="x" * 129)

    for response in (wrong_password, unknown_email, invalid_email, too_long):
        assert_unauthorized(response)
        assert_matches_contract(response, SIGN_IN, "post")


async def test_wrong_email_and_wrong_password_take_similar_time(client: httpx.AsyncClient) -> None:
    email = new_email()
    assert (await sign_up(client, email)).status_code == 201
    await sign_in(client, new_email())  # warm-up

    timings: dict[str, list[float]] = {"unknown email": [], "wrong password": []}
    for _ in range(8):
        for label, address in (("unknown email", new_email()), ("wrong password", email)):
            started = time.perf_counter()
            response = await sign_in(client, address, password=WRONG)
            timings[label].append(time.perf_counter() - started)
            assert response.status_code == 401

    unknown, wrong = (statistics.median(t) for t in timings.values())
    # Both paths run one indexed lookup and one argon2id verify (A6); a loose bound keeps a
    # busy CI runner from failing the test, while a skipped verify (about 100x faster) fails it.
    assert 0.6 < unknown / wrong < 1.6, timings


async def test_sign_in_rehashes_old_parameters(
    app: FastAPI, client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    email = new_email()
    principal = principal_of((await sign_up(client, email)).json())
    weak = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1, type=Type.ID)
    await sql(
        app,
        "UPDATE accounts SET password_hash = :h WHERE principal_id = :id",
        h=weak.hash(PASSWORD),
        id=principal,
    )

    caplog.clear()
    assert (await sign_in(client, email)).status_code == 200

    row = await account_row(app, email)
    assert row.password_hash.startswith("$argon2id$v=19$m=65536,t=3,p=1$")
    events = [getattr(record, "event", None) for record in caplog.records]
    assert "password_rehashed" in events
    assert (await sign_in(client, email)).status_code == 200


async def test_a_rehash_never_overwrites_a_hash_changed_since_the_verify(
    app: FastAPI, client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    email = new_email()
    principal = principal_of((await sign_up(client, email)).json())
    weak = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1, type=Type.ID)
    await sql(
        app,
        "UPDATE accounts SET password_hash = :h WHERE principal_id = :id",
        h=weak.hash(PASSWORD),
        id=principal,
    )
    newer = await app.state.password_hashing.hash(OTHER)  # as a reset (E1-17) would store it
    real: PasswordHashing = app.state.password_hashing

    class ChangedDuringVerify:
        """The verify succeeds with a rehash; meanwhile another request stores a new hash."""

        async def verify(self, stored: str | None, password: str) -> Verified:
            verified = await real.verify(stored, password)
            assert verified.rehashed is not None
            await sql(
                app,
                "UPDATE accounts SET password_hash = :h WHERE principal_id = :id",
                h=newer,
                id=principal,
            )
            return verified

    app.state.password_hashing = ChangedDuringVerify()
    caplog.clear()

    assert (await sign_in(client, email)).status_code == 200

    assert (await account_row(app, email)).password_hash == newer  # the newer hash survives
    events = [getattr(record, "event", None) for record in caplog.records]
    assert "signed_in" in events
    assert "password_rehashed" not in events  # logged only when the row was written


class _BarrierBeforeHash:
    """Holds every `hash` call until two requests are waiting, then lets both through."""

    def __init__(self, real: PasswordHashing) -> None:
        self._real = real
        self._barrier = asyncio.Barrier(2)

    async def hash(self, password: str) -> str:
        async with asyncio.timeout(5):  # a lost request must fail the test, not hang it
            await self._barrier.wait()
        return await self._real.hash(password)


class _NoTransactionSpy:
    """Wraps the real hasher and records whether a database connection was checked out while
    a hash or verify was about to run (the pool counts every open session's connection)."""

    def __init__(self, app: FastAPI) -> None:
        self._real: PasswordHashing = app.state.password_hashing
        self._app = app
        self.checked_out: list[int] = []

    def _record(self) -> None:
        self.checked_out.append(self._app.state.engine.pool.checkedout())

    async def hash(self, password: str) -> str:
        self._record()
        return await self._real.hash(password)

    async def verify(self, stored: str | None, password: str) -> Verified:
        self._record()
        return await self._real.verify(stored, password)


async def test_no_transaction_or_connection_is_open_while_the_hasher_runs(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    spy = _NoTransactionSpy(app)
    app.state.password_hashing = spy
    email = new_email()

    assert (await sign_up(client, email)).status_code == 201
    assert (await sign_in(client, email)).status_code == 200
    assert (await sign_in(client, email, password=WRONG)).status_code == 401
    assert (await sign_in(client, new_email())).status_code == 401

    assert spy.checked_out == [0, 0, 0, 0]


# --- logout: this device only ---


async def test_logout_ends_only_this_devices_session(client: httpx.AsyncClient) -> None:
    email = new_email()
    phone = (await sign_up(client, email)).json()
    tablet = (await sign_in(client, email)).json()

    logout = await client.post(LOGOUT, json={"refresh_token": phone["refresh_token"]})

    assert logout.status_code == 204
    assert_unauthorized(await client.post(REFRESH, json={"refresh_token": phone["refresh_token"]}))
    still = await client.post(REFRESH, json={"refresh_token": tablet["refresh_token"]})
    assert still.status_code == 200
    assert principal_of(still.json()) == principal_of(phone)


# --- logs (docs/security.md §6, A15) ---


async def test_logs_hold_no_email_password_or_token_and_a15_events_carry_the_principal(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = make_app()
    email = new_email()
    async with client_for(app, lifespan=True) as client:
        created = (await sign_up(client, email)).json()
        signed_in = (await sign_in(client, email)).json()
        await sign_in(client, email, password=WRONG)
        await sign_in(client, new_email())

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    principal = str(principal_of(created))
    events = [(line["event"], line.get("principal_id")) for line in lines if "event" in line]
    assert events == [
        ("account_created", principal),
        ("signed_in", principal),
        ("sign_in_failed", principal),
        ("sign_in_failed", None),
    ]
    raw = json.dumps(lines)
    assert email not in raw
    assert email.split("@")[0] not in raw
    assert PASSWORD not in raw
    for secret in (*created.values(), *signed_in.values()):
        if isinstance(secret, str) and len(secret) > 20:
            assert secret not in raw
            assert hashlib.sha256(secret.encode()).hexdigest() not in raw
    assert "127.0.0.1" not in raw
