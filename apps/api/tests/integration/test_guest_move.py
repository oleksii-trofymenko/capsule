"""The move from guest to account on sign-up and sign-in (E1-07c, ADR-014 R3, ADR-022), against
real Postgres, the real hasher and the E1-07b ledger writer."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from core.deletion_ledger import FILE_NAME
from tests.integration.test_accounts import SIGN_IN, SIGN_UP, WRONG, new_email, sign_up
from tests.integration.test_auth import (
    GUEST,
    assert_unauthorized,
    make_app,
    new_guest,
    principal_of,
    sql,
)
from tests.support import A15, assert_matches_contract, client_for

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

PASSWORD = "violet hedgehog 42"  # noqa: S105 - a made-up test password
LEDGER_LOG = "core.deletion_ledger"


@pytest.fixture
async def app() -> AsyncIterator[FastAPI]:
    yield make_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with client_for(app, lifespan=True) as client:
        yield client


async def _sign_up(client: httpx.AsyncClient, email: str, credential: str) -> httpx.Response:
    body = {"email": email, "password": PASSWORD, "age_confirmed": True}
    return await client.post(SIGN_UP, json=body | {"guest_credential": credential})


async def _sign_in(
    client: httpx.AsyncClient, email: str, credential: str, password: str = PASSWORD
) -> httpx.Response:
    body = {"email": email, "password": password, "guest_credential": credential}
    return await client.post(SIGN_IN, json=body)


async def _guest_rows(app: FastAPI, guest: uuid.UUID) -> dict[str, int]:
    """What is left of a guest, and its ledger rows."""
    counts = {}
    for table, column in (
        ("principals", "id"),
        ("guest_credentials", "principal_id"),
        ("refresh_families", "principal_id"),
        ("deletion_ledger", "principal_id"),
    ):
        query = f"SELECT count(*) FROM {table} WHERE {column} = :id"  # noqa: S608 - fixed names
        counts[table] = (await sql(app, query, id=guest))[0][0]
    return counts


MOVED = {"principals": 0, "guest_credentials": 0, "refresh_families": 0, "deletion_ledger": 1}
KEPT = {"principals": 1, "guest_credentials": 1, "refresh_families": 1, "deletion_ledger": 0}


async def _account_id(app: FastAPI, email: str) -> uuid.UUID | None:
    rows = await sql(app, "SELECT principal_id FROM accounts WHERE email = :email", email=email)
    return rows[0][0] if rows else None


async def _waiting_on_locks(app: FastAPI, count: int) -> None:
    """Until `count` sessions of this database wait for a lock (2 s at most)."""
    query = (
        "SELECT count(*) FROM pg_stat_activity"
        " WHERE wait_event_type = 'Lock' AND datname = current_database()"
    )
    for _ in range(200):
        if (await sql(app, query))[0][0] >= count:
            return
        await asyncio.sleep(0.01)
    pytest.fail(f"fewer than {count} sessions waited for a lock")


# --- the move ---


async def test_sign_up_moves_the_guest_and_writes_the_ledger_row_and_line(
    tmp_path: Path,
) -> None:
    app = make_app(deletion_ledger_dir=tmp_path)
    async with client_for(app, lifespan=True) as client:
        guest = await new_guest(client)
        response = await _sign_up(client, new_email(), guest["guest_credential"])
        again = await client.post(GUEST, json={"guest_credential": guest["guest_credential"]})

        assert response.status_code == 201, response.text
        assert_matches_contract(response, SIGN_UP, "post")
        assert response.json()["guest_guides_moved"] == 0
        guest_id = principal_of(guest)
        assert await _guest_rows(app, guest_id) == MOVED
        [(deleted_at,)] = await sql(
            app, "SELECT deleted_at FROM deletion_ledger WHERE principal_id = :id", id=guest_id
        )
    assert (tmp_path / FILE_NAME).read_text(encoding="ascii") == (
        f"{guest_id} {deleted_at.isoformat()}\n"
    )
    assert_unauthorized(again)  # the credential is gone for good


async def test_sign_in_moves_the_guest_even_with_a_missing_ledger_directory(
    tmp_path: Path,
) -> None:
    app = make_app(deletion_ledger_dir=tmp_path / "not-mounted")
    async with client_for(app, lifespan=True) as client:
        email = new_email()
        assert (await sign_up(client, email)).status_code == 201
        guest = await new_guest(client)
        response = await _sign_in(client, email, guest["guest_credential"])

        assert response.status_code == 200, response.text
        assert_matches_contract(response, SIGN_IN, "post")
        assert response.json()["guest_guides_moved"] == 0
        assert await _guest_rows(app, principal_of(guest)) == MOVED  # the table is the record
        me = principal_of(response.json())
        assert me == await _account_id(app, email)


@pytest.mark.parametrize("case", ["unknown", "reused", "expired", "not_a_guest"])
async def test_a_credential_that_names_no_active_guest_moves_nothing(
    case: str, app: FastAPI, client: httpx.AsyncClient
) -> None:
    other = await new_guest(client)  # never touched: nothing is matched but the credential
    guest = await new_guest(client)
    guest_id, credential = principal_of(guest), guest["guest_credential"]
    expected = dict(KEPT)
    if case == "unknown":
        credential = "not a credential ?!"
    elif case == "reused":
        assert (await _sign_up(client, new_email(), credential)).status_code == 201
        expected = MOVED
    elif case == "expired":
        await sql(
            app,
            "UPDATE principals SET last_activity_at = now() - interval '31 days' WHERE id = :id",
            id=guest_id,
        )
    else:
        await sql(app, "UPDATE principals SET kind = 'account' WHERE id = :id", id=guest_id)

    response = await _sign_up(client, new_email(), credential)

    assert response.status_code == 201, response.text
    assert response.json()["guest_guides_moved"] == 0
    assert await _guest_rows(app, guest_id) == expected
    assert await _guest_rows(app, principal_of(other)) == KEPT


async def test_a_wrong_password_moves_nothing(app: FastAPI, client: httpx.AsyncClient) -> None:
    email = new_email()
    assert (await sign_up(client, email)).status_code == 201
    guest = await new_guest(client)

    response = await _sign_in(client, email, guest["guest_credential"], password=WRONG)

    assert_unauthorized(response)
    assert await _guest_rows(app, principal_of(guest)) == KEPT


async def test_a_move_failing_halfway_changes_nothing(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    guest = await new_guest(client)
    guest_id = principal_of(guest)
    name = f"test_fail_ledger_{uuid.uuid4().hex}"
    # The ledger insert is the last step, after the guest was deleted; fail it for this guest.
    await sql(
        app,
        f"""
        CREATE FUNCTION {name}() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.principal_id = '{guest_id}' THEN RAISE EXCEPTION 'test failure'; END IF;
            RETURN NEW;
        END $$
        """,
    )
    await sql(
        app,
        f"CREATE TRIGGER {name} BEFORE INSERT ON deletion_ledger"
        f" FOR EACH ROW EXECUTE FUNCTION {name}()",
    )
    email = new_email()
    try:
        response = await _sign_up(client, email, guest["guest_credential"])
    finally:
        await sql(app, f"DROP TRIGGER {name} ON deletion_ledger")
        await sql(app, f"DROP FUNCTION {name}()")

    assert response.status_code == 500
    assert await _account_id(app, email) is None  # one transaction: no account either
    assert await _guest_rows(app, guest_id) == KEPT
    again = await client.post(GUEST, json={"guest_credential": guest["guest_credential"]})
    assert again.status_code == 200  # the guest credential still works


# --- R3: the credential row lock, on real connections ---


async def test_a_locked_credential_gets_503_and_nothing_changes(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    guest = await new_guest(client)
    guest_id = principal_of(guest)
    email = new_email()
    async with app.state.engine.connect() as blocker:
        await blocker.begin()
        await blocker.execute(
            text("SELECT 1 FROM guest_credentials WHERE principal_id = :id FOR UPDATE"),
            {"id": guest_id},
        )
        response = await _sign_up(client, email, guest["guest_credential"])
        await blocker.rollback()

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "1"
    assert_matches_contract(response, SIGN_UP, "post")
    assert await _account_id(app, email) is None
    assert await _guest_rows(app, guest_id) == KEPT
    retried = await _sign_up(client, email, guest["guest_credential"])
    assert retried.status_code == 201
    assert await _guest_rows(app, guest_id) == MOVED


async def test_two_parallel_moves_of_one_guest_move_it_once(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = make_app()  # after capsys, so the JSON handler writes to the captured stdout
    emails = [new_email(), new_email()]
    async with client_for(app, lifespan=True) as client:
        guest = await new_guest(client)
        guest_id = principal_of(guest)
        async with app.state.engine.connect() as blocker:
            # A shared lock holds both moves at the credential row, so they race once it goes.
            await blocker.begin()
            await blocker.execute(
                text("SELECT 1 FROM guest_credentials WHERE principal_id = :id FOR SHARE"),
                {"id": guest_id},
            )
            tasks = [
                asyncio.create_task(_sign_up(client, email, guest["guest_credential"]))
                for email in emails
            ]
            await _waiting_on_locks(app, 2)
            await blocker.rollback()
        responses = await asyncio.gather(*tasks)

        assert [r.status_code for r in responses] == [201, 201]
        assert await _guest_rows(app, guest_id) == MOVED
        accounts = {await _account_id(app, email) for email in emails}
    events = [line for line in _log_lines(capsys) if line.get("event") == "guest_data_moved"]
    assert len(events) == 1
    assert uuid.UUID(events[0]["principal_id"]) in accounts


async def test_a_guest_sign_in_racing_a_move_gets_401_not_500(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    guest = await new_guest(client)
    credential = guest["guest_credential"]
    async with app.state.engine.connect() as blocker:
        # Stalls the real move at its last step, after it locked the credential and deleted
        # the guest; the guest sign-in then queues behind the move's row lock.
        await blocker.begin()
        await blocker.execute(text("LOCK TABLE deletion_ledger IN EXCLUSIVE MODE"))
        move = asyncio.create_task(_sign_up(client, new_email(), credential))
        await _waiting_on_locks(app, 1)
        sign_in = asyncio.create_task(client.post(GUEST, json={"guest_credential": credential}))
        await _waiting_on_locks(app, 2)
        await blocker.rollback()

    assert (await move).status_code == 201
    assert_unauthorized(await sign_in)
    assert await _guest_rows(app, principal_of(guest)) == MOVED


# --- A15 ---


def _log_lines(capsys: pytest.CaptureFixture[str]) -> list[dict[str, Any]]:
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


async def test_a15_guest_data_moved_carries_the_account_and_the_count_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = make_app()  # after capsys, so the JSON handler writes to the captured stdout
    email = new_email()
    async with client_for(app, lifespan=True) as client:
        guest = await new_guest(client)
        response = await _sign_up(client, email, guest["guest_credential"])
        account = await _account_id(app, email)

    lines = _log_lines(capsys)
    a15 = [line for line in lines if line["logger"] == A15]
    assert [(line["event"], line["principal_id"]) for line in a15] == [
        ("guest_created", str(principal_of(guest))),
        ("account_created", str(account)),
        ("guest_data_moved", str(account)),
    ]
    assert a15[-1]["msg"] == "guest_data_moved count=0"
    raw = json.dumps(lines)
    for secret in (email, guest["guest_credential"], *response.json().values()):
        if isinstance(secret, str) and len(secret) > 10:
            assert secret not in raw
    assert "127.0.0.1" not in raw
    # The guest id appears after the move only where ADR-022 wants it: the failed append (the
    # directory is unset here), for restore step 2.
    guest_id = str(principal_of(guest))
    after = [line for line in lines[lines.index(a15[0]) + 1 :] if guest_id in json.dumps(line)]
    assert [(line["logger"], line["event"]) for line in after] == [
        (LEDGER_LOG, "ledger_append_failed")
    ]
