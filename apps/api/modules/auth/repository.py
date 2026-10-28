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
_FIND_ACTIVE_GUEST = text(
    f"""
    SELECT p.id FROM guest_credentials c JOIN principals p ON p.id = c.principal_id
    WHERE c.credential_hash = :hash AND p.kind = 'guest' AND {_GUEST_ACTIVE}
    """  # noqa: S608 - a fixed fragment; values are bound parameters
)
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
           t.successor_hash, s.state AS successor_state
    FROM refresh_tokens t LEFT JOIN refresh_tokens s ON s.token_hash = t.successor_hash
    WHERE t.token_hash = :hash
    """
)
_ROTATE = text(
    """
    UPDATE refresh_tokens SET state = 'rotated', rotated_at = now(), successor_hash = :successor
    WHERE token_hash = :hash AND state = 'current'
    """
)
_SUPERSEDE = text(
    "UPDATE refresh_tokens SET state = 'superseded' WHERE token_hash = :hash AND state = 'current'"
)
# rotated_at keeps the first rotation time; successor_hash follows the live chain.
_USE_GRACE = text(
    """
    UPDATE refresh_tokens SET grace_used_at = now(), successor_hash = :successor
    WHERE token_hash = :hash AND state = 'rotated' AND grace_used_at IS NULL
    """
)
_TOUCH_FAMILY = text("UPDATE refresh_families SET last_refreshed_at = now() WHERE id = :id")
_REVOKE_FAMILY = text("UPDATE refresh_families SET revoked_at = now() WHERE id = :id")
_LOGOUT = text(
    """
    UPDATE refresh_families f SET revoked_at = now()
    FROM refresh_tokens t
    WHERE t.token_hash = :hash AND f.id = t.family_id AND f.revoked_at IS NULL
    RETURNING f.principal_id
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
    successor_hash: bytes | None
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
    return TokenState(
        row.state,
        row.grace_used,
        bool(row.in_grace_window),
        row.successor_hash,
        row.successor_state,
    )


async def rotate_token(session: AsyncSession, token_hash: bytes, successor: bytes) -> None:
    await session.execute(_ROTATE, {"hash": token_hash, "successor": successor})


async def use_grace(
    session: AsyncSession, token_hash: bytes, superseded: bytes, successor: bytes
) -> None:
    """ADR-014 order: the old successor stops being `current` before the new token exists."""
    await session.execute(_SUPERSEDE, {"hash": superseded})
    await session.execute(_USE_GRACE, {"hash": token_hash, "successor": successor})


async def insert_current_token(
    session: AsyncSession, family_id: uuid.UUID, token_hash: bytes
) -> None:
    """The family's new `current` token; every success also counts as the family's refresh."""
    await session.execute(_INSERT_TOKEN, {"hash": token_hash, "family_id": family_id})
    await session.execute(_TOUCH_FAMILY, {"id": family_id})


async def revoke_family(session: AsyncSession, family_id: uuid.UUID) -> None:
    await session.execute(_REVOKE_FAMILY, {"id": family_id})


async def revoke_family_of(session: AsyncSession, token_hash: bytes) -> uuid.UUID | None:
    """Logout in one statement. Returns the principal only when a live family was revoked."""
    principal_id: uuid.UUID | None = (
        await session.execute(_LOGOUT, {"hash": token_hash})
    ).scalar_one_or_none()
    return principal_id
