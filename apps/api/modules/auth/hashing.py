"""argon2id password hashing behind a bounded semaphore (ADR-014, ADR-023).

Order in a request: rate limits (E1-08) first, then a slot here, then the hash in a worker thread.
Call outside any database transaction: a hash takes 100-300 ms and must not hold a row lock.
"""

import asyncio
import contextlib
import contextvars
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

SLOTS = 4  # at most 4 hashes at once: about 256 MiB peak (4 x 64 MiB)
ACQUIRE_TIMEOUT_S = 1.0
RETRY_AFTER_S = 1

# ADR-014: m = 64 MiB, t = 3, p = 1, 16-byte salt, 32-byte hash.
HASHER = PasswordHasher(
    time_cost=3, memory_cost=65536, parallelism=1, hash_len=32, salt_len=16, type=Type.ID
)
# A hash of a random, discarded password with the parameters above. Unknown emails are verified
# against it through the same path, so they cost the same time (A6). It never matches.
DUMMY_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=1$SOE89w1zKYhYh2CRq+61FQ"
    "$kdcdjbhUtZWBmLGmkREFkThBub8AgijUtwf/fc3qLvo"
)

logger = logging.getLogger(__name__)


class HasherBusyError(Exception):
    """No slot within the acquire timeout. No hash ran; answer 503 with `Retry-After`."""


@dataclass(frozen=True)
class Verified:
    ok: bool
    rehashed: str | None = None  # a new hash to store when the stored one has old parameters


def _verify(stored: str | None, password: str) -> Verified:
    try:
        HASHER.verify(DUMMY_HASH if stored is None else stored, password)
    except VerificationError:
        return Verified(ok=False)
    except InvalidHashError:
        logger.error("stored password hash is not valid", extra={"event": "invalid_password_hash"})
        return Verified(ok=False)
    if stored is None:  # no password is known to match the dummy hash; never let one through
        return Verified(ok=False)
    rehashed = HASHER.hash(password) if HASHER.check_needs_rehash(stored) else None
    return Verified(ok=True, rehashed=rehashed)


class PasswordHashing:
    """One per app, created in the lifespan. Passwords come in NFC (`rules.normalise_password`)."""

    def __init__(self, executor: ThreadPoolExecutor) -> None:
        self._executor = executor
        self._slots = asyncio.Semaphore(SLOTS)

    async def hash(self, password: str) -> str:
        return await self._run(HASHER.hash, password)

    async def verify(self, stored: str | None, password: str) -> Verified:
        """`stored=None` (unknown email) verifies against the dummy hash and is never ok. A match
        whose hash has old parameters is rehashed in the same slot."""
        return await self._run(_verify, stored, password)

    async def _run[**P, T](self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        try:
            async with asyncio.timeout(ACQUIRE_TIMEOUT_S):
                await self._slots.acquire()
        except TimeoutError:
            logger.warning("password hasher busy", extra={"event": "hasher_busy"})
            raise HasherBusyError from None
        # The context carries the request id into the thread's log lines.
        context = contextvars.copy_context()

        def call() -> T:
            return context.run(fn, *args, **kwargs)

        try:
            future = self._executor.submit(call)
        except BaseException:
            self._slots.release()
            raise
        # The slot is freed when the thread is done, not when the caller stops waiting: a
        # cancelled request whose hash is already running keeps its slot until the hash ends.
        future.add_done_callback(self._release_from(asyncio.get_running_loop()))
        return await asyncio.wrap_future(future)

    def _release_from(self, loop: asyncio.AbstractEventLoop) -> Callable[[object], None]:
        def release(_: object) -> None:
            # A closed loop (shutdown) has no one waiting for the slot.
            with contextlib.suppress(RuntimeError):
                loop.call_soon_threadsafe(self._slots.release)

        return release


def create_hash_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=SLOTS, thread_name_prefix="password-hash")
