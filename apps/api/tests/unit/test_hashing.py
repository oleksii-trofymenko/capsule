"""argon2id parameters, the dummy hash and the hash semaphore (ADR-014)."""

import asyncio
import base64
import logging
import threading
import time
from collections.abc import AsyncIterator, Callable

import pytest
from argon2 import PasswordHasher, Type, extract_parameters

from main import create_app
from modules.auth import hashing
from modules.auth.hashing import (
    DUMMY_HASH,
    HASHER,
    HasherBusyError,
    PasswordHashing,
    create_hash_executor,
)
from tests.support import dummy_settings

pytestmark = pytest.mark.anyio

PASSWORD = "correct horse battery"  # noqa: S105 - a made-up test password


@pytest.fixture
async def hasher() -> AsyncIterator[PasswordHashing]:
    executor = create_hash_executor()
    yield PasswordHashing(executor)
    executor.shutdown(wait=True, cancel_futures=True)


def _b64(part: str) -> bytes:
    return base64.b64decode(part + "=" * (-len(part) % 4))


def test_parameters_are_the_adr_014_ones() -> None:
    params = HASHER._parameters
    assert params.type is Type.ID
    assert (params.memory_cost, params.time_cost, params.parallelism) == (65536, 3, 1)
    assert (params.salt_len, params.hash_len) == (16, 32)


def test_dummy_hash_has_the_same_parameters_and_needs_no_rehash() -> None:
    assert extract_parameters(DUMMY_HASH) == HASHER._parameters
    assert not HASHER.check_needs_rehash(DUMMY_HASH)


async def test_hash_uses_the_parameters_and_verifies(hasher: PasswordHashing) -> None:
    stored = await hasher.hash(PASSWORD)

    assert stored.startswith("$argon2id$v=19$m=65536,t=3,p=1$")
    salt, digest = stored.split("$")[-2:]
    assert (len(_b64(salt)), len(_b64(digest))) == (16, 32)
    assert PASSWORD not in stored
    assert await hasher.verify(stored, PASSWORD) == hashing.Verified(ok=True)
    assert await hasher.verify(stored, PASSWORD + "x") == hashing.Verified(ok=False)


async def test_unknown_email_runs_the_dummy_hash_and_never_matches(
    hasher: PasswordHashing, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    class Spy:
        def verify(self, stored: str, password: str) -> bool:
            seen.append(stored)
            return HASHER.verify(stored, password)

    monkeypatch.setattr(hashing, "HASHER", Spy())

    assert await hasher.verify(None, PASSWORD) == hashing.Verified(ok=False)
    assert seen == [DUMMY_HASH]  # the same path and cost as a wrong password (A6)


async def test_old_parameters_are_rehashed_in_the_same_call(hasher: PasswordHashing) -> None:
    weak = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1, type=Type.ID)
    result = await hasher.verify(weak.hash(PASSWORD), PASSWORD)

    assert result.ok
    assert result.rehashed is not None
    assert not HASHER.check_needs_rehash(result.rehashed)
    assert HASHER.verify(result.rehashed, PASSWORD)


async def test_a_corrupt_stored_hash_fails_and_logs_no_value(
    hasher: PasswordHashing, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR, logger=hashing.__name__):
        result = await hasher.verify("not-a-hash", PASSWORD)

    assert result == hashing.Verified(ok=False)
    assert [getattr(r, "event", None) for r in caplog.records] == ["invalid_password_hash"]
    assert "not-a-hash" not in caplog.text
    assert PASSWORD not in caplog.text


class _BlockingHasher:
    """Stands in for HASHER.hash: each call blocks its thread until `release` is set."""

    def __init__(self) -> None:
        self.release = threading.Event()
        self.started = 0
        self.running = 0
        self.most_running = 0
        self._lock = threading.Lock()

    def hash(self, _: str) -> str:
        with self._lock:
            self.started += 1
            self.running += 1
            self.most_running = max(self.most_running, self.running)
        self.release.wait(5)
        with self._lock:
            self.running -= 1
        return "hashed"


async def _until(condition: Callable[[], bool], timeout_s: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not reached"
        await asyncio.sleep(0.01)


async def _fill_slots(hasher: PasswordHashing, fake: _BlockingHasher) -> list[asyncio.Task[str]]:
    tasks = [asyncio.create_task(hasher.hash(PASSWORD)) for _ in range(hashing.SLOTS)]
    await _until(lambda: fake.started == hashing.SLOTS)
    return tasks


async def test_a_fifth_caller_times_out_after_1_s_and_runs_no_hash(
    hasher: PasswordHashing, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    fake = _BlockingHasher()
    monkeypatch.setattr(hashing, "HASHER", fake)
    tasks = await _fill_slots(hasher, fake)

    started = time.monotonic()
    with caplog.at_level(logging.WARNING, logger=hashing.__name__), pytest.raises(HasherBusyError):
        await hasher.hash(PASSWORD)
    waited = time.monotonic() - started

    assert 0.9 <= waited < 1.5
    assert fake.started == hashing.SLOTS
    events = [(r.levelname, getattr(r, "event", None)) for r in caplog.records]
    assert events == [("WARNING", "hasher_busy")]
    assert PASSWORD not in caplog.text

    fake.release.set()
    assert await asyncio.gather(*tasks) == ["hashed"] * hashing.SLOTS
    assert fake.most_running == hashing.SLOTS


async def test_a_cancelled_caller_keeps_its_slot_until_the_hash_ends(
    hasher: PasswordHashing, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hashing, "ACQUIRE_TIMEOUT_S", 0.2)
    fake = _BlockingHasher()
    monkeypatch.setattr(hashing, "HASHER", fake)
    tasks = await _fill_slots(hasher, fake)

    tasks[0].cancel()
    with pytest.raises(asyncio.CancelledError):
        await tasks[0]
    # The cancelled caller's thread is still hashing, so its slot is not free.
    with pytest.raises(HasherBusyError):
        await hasher.hash(PASSWORD)
    assert fake.started == hashing.SLOTS

    fake.release.set()
    await asyncio.gather(*tasks[1:])
    await _until(lambda: fake.running == 0)
    assert await hasher.hash(PASSWORD) == "hashed"  # every slot came back
    assert fake.most_running == hashing.SLOTS


async def test_the_lifespan_creates_the_hasher_and_stops_its_threads() -> None:
    app = create_app(dummy_settings())
    async with app.router.lifespan_context(app):
        hasher = app.state.password_hashing
        assert isinstance(hasher, PasswordHashing)

    with pytest.raises(RuntimeError):  # the executor is shut down: no hash after shutdown
        await hasher.hash(PASSWORD)
