"""SQL for the auth tables. Bound parameters only; callers own the transaction."""

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from modules.auth.tokens import Kind

_INSERT_PRINCIPAL = text("INSERT INTO principals (kind) VALUES (:kind) RETURNING id")
_INSERT_CREDENTIAL = text(
    "INSERT INTO guest_credentials (principal_id, credential_hash) VALUES (:principal_id, :hash)"
)
_INSERT_FAMILY = text(
    "INSERT INTO refresh_families (principal_id) VALUES (:principal_id) RETURNING id"
)
_INSERT_TOKEN = text(
    "INSERT INTO refresh_tokens (token_hash, family_id, state)"
    " VALUES (:hash, :family_id, 'current')"
)
# ADR-014: an expired guest gets the same answer as an unknown credential, even before the purge.
# Shared by the guest sign-in and refresh, so both expire a guest at the same moment.
_GUEST_ACTIVE = "p.last_activity_at >= now() - make_interval(days => :retention_days)"
_ACTIVE_GUEST = f"""
    SELECT p.id FROM guest_credentials c JOIN principals p ON p.id = c.principal_id
    WHERE c.credential_hash = :hash AND p.kind = 'guest' AND {_GUEST_ACTIVE}
"""  # noqa: S608 - a fixed fragment; values are bound parameters
# R3: FOR SHARE queues a guest sign-in behind a move of the same guest, which holds FOR UPDATE;
# once the move commits, the row is gone and the sign-in gets the one 401, not a foreign-key 500.
_FIND_ACTIVE_GUEST = text(_ACTIVE_GUEST + " FOR SHARE OF c")
_PRINCIPAL_KIND = text("SELECT kind FROM principals WHERE id = :id")
# ADR-022: at most one write per principal per hour.
_TOUCH = text(
    """
    UPDATE principals SET last_activity_at = now()
    WHERE id = :id AND last_activity_at < now() - interval '1 hour'
    """
)
# A slow database must not hold the connection after the response has gone.
_TOUCH_TIMEOUT = text("SET LOCAL statement_timeout = '2s'")


async def insert_principal(session: AsyncSession, kind: Kind) -> uuid.UUID:
    principal_id: uuid.UUID = (
        await session.execute(_INSERT_PRINCIPAL, {"kind": kind})
    ).scalar_one()
    return principal_id


async def insert_guest_credential(
    session: AsyncSession, principal_id: uuid.UUID, credential_hash: bytes
) -> None:
    await session.execute(
        _INSERT_CREDENTIAL, {"principal_id": principal_id, "hash": credential_hash}
    )


async def insert_family_with_token(
    session: AsyncSession, principal_id: uuid.UUID, token_hash: bytes
) -> None:
    family_id = (await session.execute(_INSERT_FAMILY, {"principal_id": principal_id})).scalar_one()
    await session.execute(_INSERT_TOKEN, {"hash": token_hash, "family_id": family_id})


async def find_active_guest(
    session: AsyncSession, credential_hash: bytes, retention_days: int
) -> uuid.UUID | None:
    params = {"hash": credential_hash, "retention_days": retention_days}
    principal_id: uuid.UUID | None = (
        await session.execute(_FIND_ACTIVE_GUEST, params)
    ).scalar_one_or_none()
    return principal_id


# --- the move from guest to account (ADR-014 R3, ADR-022): one transaction, which first calls
# set_lock_timeout and locks the credential row, so only one move deletes a given guest.

_LOCK_ACTIVE_GUEST = text(_ACTIVE_GUEST + " FOR UPDATE OF c")
# Cascades to the guest's credential and refresh families (and their tokens).
_DELETE_GUEST = text("DELETE FROM principals WHERE id = :id AND kind = 'guest'")


async def lock_active_guest(
    session: AsyncSession, credential_hash: bytes, retention_days: int
) -> uuid.UUID | None:
    """None for an unknown, expired or non-guest credential, or one a concurrent move used."""
    params = {"hash": credential_hash, "retention_days": retention_days}
    principal_id: uuid.UUID | None = (
        await session.execute(_LOCK_ACTIVE_GUEST, params)
    ).scalar_one_or_none()
    return principal_id


async def move_guest_data(session: AsyncSession, guest_id: uuid.UUID, account_id: uuid.UUID) -> int:
    """Moves every guest-owned row to the account; returns the number of guides moved. The guest
    owns nothing but its credential and sessions until E3 adds guides, which move here."""
    return 0


async def delete_guest(session: AsyncSession, guest_id: uuid.UUID) -> None:
    await session.execute(_DELETE_GUEST, {"id": guest_id})


async def principal_kind(session: AsyncSession, principal_id: uuid.UUID) -> Kind | None:
    kind: Kind | None = (
        await session.execute(_PRINCIPAL_KIND, {"id": principal_id})
    ).scalar_one_or_none()
    return kind


async def touch_last_activity(conn: AsyncConnection, principal_id: uuid.UUID) -> None:
    """Call inside a transaction: the timeout bounds this update only, lock waits included."""
    await conn.execute(_TOUCH_TIMEOUT)
    await conn.execute(_TOUCH, {"id": principal_id})


# --- refresh and logout (ADR-014): one transaction each, which first calls set_lock_timeout.

# A lock wait past this ends in SQLSTATE 55P03; the caller rolls back and answers 503.
_LOCK_TIMEOUT = text("SET LOCAL lock_timeout = '2s'")
# The family row is the lock every refresh of the family queues on. Only a live family is
# returned, and so locked: not revoked, refreshed within 30 days, created within 90 days and, for
# a guest, inside the retention (the guest sign-in predicate). Re-checked after a lock wait.
_LOCK_LIVE_FAMILY = text(
    f"""
    SELECT f.id, f.principal_id, p.kind
    FROM refresh_tokens t
    JOIN refresh_families f ON f.id = t.family_id
    JOIN principals p ON p.id = f.principal_id
    WHERE t.token_hash = :hash
      AND f.revoked_at IS NULL
      AND f.last_refreshed_at >= now() - interval '30 days'
      AND f.created_at >= now() - interval '90 days'
      AND (p.kind <> 'guest' OR {_GUEST_ACTIVE})
    FOR UPDATE OF f
    """  # noqa: S608 - a fixed fragment; values are bound parameters
)
# Read only while the family lock is held. statement_timestamp(), not now(): the transaction may
# have started up to 2 s earlier, while it waited for the lock.
_TOKEN_STATE = text(
    """
    SELECT t.state, t.grace_used_at IS NOT NULL AS grace_used,
           t.rotated_at >= statement_timestamp() - interval '30 seconds' AS in_grace_window,
           s.state AS successor_state
    FROM refresh_tokens t LEFT JOIN refresh_tokens s ON s.token_hash = t.successor_hash
    WHERE t.token_hash = :hash
    """
)
# Writes use statement_timestamp() too, on the same clock as the grace-window check.
_ROTATE = text(
    """
    UPDATE refresh_tokens
    SET state = 'rotated', rotated_at = statement_timestamp(), successor_hash = :successor
    WHERE token_hash = :hash AND state = 'current'
    """
)
# Grace only runs when the presented token's successor is the family's one `current` token.
_SUPERSEDE = text(
    "UPDATE refresh_tokens SET state = 'superseded' WHERE family_id = :family_id"
    " AND state = 'current'"
)
# rotated_at keeps the first rotation time; successor_hash follows the live chain.
_USE_GRACE = text(
    """
    UPDATE refresh_tokens SET grace_used_at = statement_timestamp(), successor_hash = :successor
    WHERE token_hash = :hash AND state = 'rotated' AND grace_used_at IS NULL
    """
)
_TOUCH_FAMILY = text(
    "UPDATE refresh_families SET last_refreshed_at = statement_timestamp() WHERE id = :id"
)
_REVOKE_FAMILY = text("UPDATE refresh_families SET revoked_at = now() WHERE id = :id")
# The token's state tells a logout (`current`) from a used token presented again (A15 reuse).
_LOGOUT = text(
    """
    UPDATE refresh_families f SET revoked_at = now()
    FROM refresh_tokens t
    WHERE t.token_hash = :hash AND f.id = t.family_id AND f.revoked_at IS NULL
    RETURNING f.principal_id, t.state
    """
)


@dataclass(frozen=True)
class LiveFamily:
    id: uuid.UUID
    principal_id: uuid.UUID
    kind: Kind


@dataclass(frozen=True)
class TokenState:
    state: str
    grace_used: bool
    in_grace_window: bool
    successor_state: str | None


async def set_lock_timeout(session: AsyncSession) -> None:
    await session.execute(_LOCK_TIMEOUT)


async def lock_live_family(
    session: AsyncSession, token_hash: bytes, retention_days: int
) -> LiveFamily | None:
    params = {"hash": token_hash, "retention_days": retention_days}
    row = (await session.execute(_LOCK_LIVE_FAMILY, params)).one_or_none()
    return None if row is None else LiveFamily(row.id, row.principal_id, row.kind)


async def token_state(session: AsyncSession, token_hash: bytes) -> TokenState | None:
    row = (await session.execute(_TOKEN_STATE, {"hash": token_hash})).one_or_none()
    if row is None:
        return None
    # in_grace_window is NULL for a token that was never rotated.
    return TokenState(row.state, row.grace_used, bool(row.in_grace_window), row.successor_state)


async def rotate_token(session: AsyncSession, token_hash: bytes, successor: bytes) -> None:
    await session.execute(_ROTATE, {"hash": token_hash, "successor": successor})


async def use_grace(
    session: AsyncSession, token_hash: bytes, family_id: uuid.UUID, successor: bytes
) -> None:
    """ADR-014 order: the old successor stops being `current` before the new token exists."""
    await session.execute(_SUPERSEDE, {"family_id": family_id})
    await session.execute(_USE_GRACE, {"hash": token_hash, "successor": successor})


async def insert_current_token(
    session: AsyncSession, family_id: uuid.UUID, token_hash: bytes
) -> None:
    """The family's new `current` token; every success also counts as the family's refresh."""
    await session.execute(_INSERT_TOKEN, {"hash": token_hash, "family_id": family_id})
    await session.execute(_TOUCH_FAMILY, {"id": family_id})


async def revoke_family(session: AsyncSession, family_id: uuid.UUID) -> None:
    await session.execute(_REVOKE_FAMILY, {"id": family_id})


@dataclass(frozen=True)
class RevokedFamily:
    principal_id: uuid.UUID
    presented_state: str  # not `current`: a used (rotated or superseded) token came back


async def revoke_family_of(session: AsyncSession, token_hash: bytes) -> RevokedFamily | None:
    """Logout in one statement. Returns a value only when a live family was revoked."""
    row = (await session.execute(_LOGOUT, {"hash": token_hash})).one_or_none()
    return None if row is None else RevokedFamily(row.principal_id, row.state)


# --- accounts (E1-07): the email is stored normalised (modules/auth/rules.py).

_ACCOUNT_BY_EMAIL = text("SELECT principal_id, password_hash FROM accounts WHERE email = :email")
_INSERT_ACCOUNT = text(
    """
    INSERT INTO accounts (principal_id, email, password_hash, age_confirmed_at)
    VALUES (:principal_id, :email, :password_hash, now())
    """
)
# Compare-and-set: a hash changed meanwhile (E1-17 reset) is never overwritten by a rehash.
_REHASH = text(
    """
    UPDATE accounts SET password_hash = :new
    WHERE principal_id = :principal_id AND password_hash = :old
    """
)
ACCOUNTS_EMAIL_KEY = "accounts_email_key"


@dataclass(frozen=True)
class Account:
    principal_id: uuid.UUID
    password_hash: str


async def find_account(session: AsyncSession, email: str) -> Account | None:
    row = (await session.execute(_ACCOUNT_BY_EMAIL, {"email": email})).one_or_none()
    return None if row is None else Account(row.principal_id, row.password_hash)


async def insert_account(
    session: AsyncSession, principal_id: uuid.UUID, email: str, password_hash: str
) -> None:
    params = {"principal_id": principal_id, "email": email, "password_hash": password_hash}
    await session.execute(_INSERT_ACCOUNT, params)


async def replace_password_hash(
    session: AsyncSession, principal_id: uuid.UUID, old: str, new: str
) -> bool:
    """False when the stored hash changed since it was read: the newer hash stays."""
    params = {"principal_id": principal_id, "old": old, "new": new}
    result = await session.execute(_REHASH, params)
    return bool(getattr(result, "rowcount", 0) == 1)
